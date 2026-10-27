"""Put one employee to work on Nautilus: role prompt as system prompt, workspace tools, a
`final_output` tool for the structured handoff, and permissions derived from the manifest
(a ceiling) and the mission's execution approval."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from app.platform.nautilus.loop import AgentLoop, AgentLoopConfig, AgentRunResult
from app.platform.nautilus.messages import ChatFn, ToolCall, user_message
from app.platform.nautilus.permissions import PermissionPolicy
from app.platform.nautilus.schema_check import schema_errors
from app.platform.nautilus.tools import Tool, ToolRegistry
from app.platform.nautilus.workspace_tools import build_workspace_tools
from app.platform.orca.execution_policy import check_command_allowed
from app.platform.orca.sandbox_commands import is_lockfile, run_sandboxed
from app.platform.orca.workforce import Employee

DEFAULT_MAX_TURNS = 30
SANDBOX_COMMAND_TIMEOUT = 300
NUDGE = "You finished without calling final_output. Call final_output now with your result."
# Out of turns with no result: one short last chance to hand over what was learned, so the work (and
# the money spent on it) isn't thrown away. Found in the real-code pilot: an Audit of a 230-file app
# used all 60 turns reading files and returned nothing.
WRAP_UP = ("You have used your whole turn budget. Stop reading and call final_output NOW with what you "
           "have learned so far. Where you couldn't check something, say so (e.g. inference=true).")
WRAP_UP_TURNS = 3


@dataclass
class EmployeeResult:
    output: Optional[Dict[str, Any]]
    run: AgentRunResult


def permissions_for(employee: Employee, *, allow_writes: bool, allow_execution: bool,
                    workspace_root: Optional[str] = None,
                    write_allowed: Optional[Callable[[str], bool]] = None) -> PermissionPolicy:
    """The manifest mode is a ceiling: a read_only employee never writes. `auto` is never used:
    every write and command goes through the approver, and a command that isn't read-only runs
    only if the founder approved execution for the mission AND Orca's execution policy allows it."""
    if employee.permission_mode == "read_only":
        return PermissionPolicy("read_only")
    mode = "smart" if employee.permission_mode == "auto" else employee.permission_mode

    def approver(call: ToolCall) -> bool:
        if call.name == "write_file":  # write_allowed: files another task is building side by side are off limits
            return allow_writes and (write_allowed is None or write_allowed(str(call.arguments.get("path") or "")))
        if call.name == "run_command":
            command = str(call.arguments.get("command") or "")
            return allow_execution and check_command_allowed(command, workspace_root)[0]
        return False

    return PermissionPolicy(mode, approver=approver)


def _sandboxed_command_tool(tool: Tool, workspace_root: str) -> Tool:
    """Same tool, but the command runs in the container sandbox (client missions)."""
    def run_command(args: Dict[str, Any]) -> str:
        result = run_sandboxed(workspace_root, str(args["command"]), SANDBOX_COMMAND_TIMEOUT)
        return f"exit_code: {result['exit_code']}\n{result['output']}"

    return Tool(tool.name, tool.description + " Runs in an isolated container (no network).", tool.parameters,
                run_command, read_only=tool.read_only)


def _no_lockfile_writes(tool: Tool) -> Tool:
    """Client missions: lockfiles are rebuilt by the package manager, never written by hand."""
    def write_file(args: Dict[str, Any]) -> str:
        if is_lockfile(str(args.get("path") or "")):
            return ("Error: lockfiles are never edited by hand (their checksums can't be written correctly). "
                    "Change package.json (or requirements.txt) only: after your turn Orca runs the project's "
                    "package manager, which updates the lockfile and reinstalls before the checks run.")
        return tool.handler(args)

    return Tool(tool.name, tool.description, tool.parameters, write_file, read_only=tool.read_only)


def _locked_tool(tool: Tool, lock: threading.Lock) -> Tool:
    """Tasks built side by side share the workspace: their commands take turns."""
    def run(args: Dict[str, Any]) -> str:
        with lock:
            return tool.handler(args)

    return Tool(tool.name, tool.description, tool.parameters, run, read_only=tool.read_only)


def _final_output_tool(schema: Dict[str, Any], sink: Dict[str, Any]) -> Tool:
    def record(arguments: Dict[str, Any]) -> str:
        errors = schema_errors(arguments, schema)
        if errors:
            raise ValueError("final_output does not match the required schema: " + "; ".join(errors))
        sink["value"] = arguments
        return "Recorded. Finish now with a one-line confirmation."

    return Tool("final_output", "Submit your structured result. Call exactly once, when done.",
                schema, record, read_only=True)


def run_employee(employee: Employee, *, assignment: str, workspace_root: str, chat: ChatFn,
                 output_schema: Dict[str, Any], allow_writes: bool, allow_execution: bool,
                 max_turns: int = DEFAULT_MAX_TURNS, sandboxed: bool = False,
                 usage_sink: Optional[List[Dict[str, Any]]] = None,
                 on_event: Optional[Callable[[str, Dict[str, Any]], None]] = None,
                 write_allowed: Optional[Callable[[str], bool]] = None,
                 command_lock: Optional[threading.Lock] = None) -> EmployeeResult:
    """`usage_sink` (e.g. Mission.usage) gets one entry per provider/model this run used."""
    sink: Dict[str, Any] = {}
    tools = ToolRegistry([_sandboxed_command_tool(t, workspace_root) if sandboxed and t.name == "run_command" else
                          _no_lockfile_writes(t) if sandboxed and t.name == "write_file" else
                          _locked_tool(t, command_lock) if command_lock and t.name == "run_command" else t
                          for t in build_workspace_tools(workspace_root)])
    tools.register(_final_output_tool(output_schema, sink))
    execution_note = ("Code execution IS approved for this mission: you may run commands in the workspace."
                      if allow_execution else
                      "Code execution is NOT approved: do not run the application, its tests or interpreters.")
    if sandboxed:
        execution_note += ("\nThis is a client's existing codebase. Commands run in an isolated container "
                           "without network, on a fresh copy each time (files you change there are not kept; "
                           "use write_file). Installed dependencies are already in place. Make focused changes "
                           "that match the existing code style; don't upgrade or reformat unrelated code. "
                           "To change a dependency, edit package.json (or requirements.txt) only, never a lockfile: "
                           "after your turn Orca runs the package manager (with network) to update the lockfile and "
                           "reinstall, then the checks run on the new versions. Commands that need the internet "
                           "(pnpm audit, npm view, installs) fail here.")
    loop = AgentLoop(
        chat=chat, tools=tools, workspace_root=workspace_root,
        system_prompt=employee.role_prompt + "\n\n" + execution_note,
        permissions=permissions_for(employee, allow_writes=allow_writes, allow_execution=allow_execution,
                                    workspace_root=workspace_root, write_allowed=write_allowed),
        config=AgentLoopConfig(max_turns=max_turns),
        on_event=on_event,
    )
    run = loop.run(assignment)
    if "value" not in sink and run.status in ("completed", "max_turns"):
        first, ran_out = run.usage, run.status == "max_turns"
        if ran_out:
            loop.config = AgentLoopConfig(max_turns=WRAP_UP_TURNS)
            if on_event is not None:
                on_event("wrap_up", {"turns": WRAP_UP_TURNS})
        run = loop.resume(run.messages + [user_message(WRAP_UP if ran_out else NUDGE)])
        for key, totals in first.items():  # count both runs
            merged = run.usage.setdefault(key, {"provider": totals["provider"], "model": totals["model"]})
            for field_name in ("calls", "input", "cached", "output"):
                merged[field_name] = merged.get(field_name, 0) + totals.get(field_name, 0)
    if usage_sink is not None:
        usage_sink.extend({"employee": employee.employee_id, **totals} for totals in run.usage.values())
    return EmployeeResult(sink.get("value"), run)
