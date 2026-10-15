"""Put one employee to work on Nautilus: role prompt as system prompt, workspace tools, a
`final_output` tool for the structured handoff, and permissions derived from the manifest
(a ceiling) and the mission's execution approval."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.platform.nautilus.loop import AgentLoop, AgentLoopConfig, AgentRunResult
from app.platform.nautilus.messages import ChatFn, ToolCall, user_message
from app.platform.nautilus.permissions import PermissionPolicy
from app.platform.nautilus.schema_check import schema_errors
from app.platform.nautilus.tools import Tool, ToolRegistry
from app.platform.nautilus.workspace_tools import build_workspace_tools
from app.platform.orca.execution_policy import check_command_allowed
from app.platform.orca.workforce import Employee

DEFAULT_MAX_TURNS = 30
NUDGE = "You finished without calling final_output. Call final_output now with your result."


@dataclass
class EmployeeResult:
    output: Optional[Dict[str, Any]]
    run: AgentRunResult


def permissions_for(employee: Employee, *, allow_writes: bool, allow_execution: bool,
                    workspace_root: Optional[str] = None) -> PermissionPolicy:
    """The manifest mode is a ceiling: a read_only employee never writes. `auto` is never used:
    every write and command goes through the approver, and a command that isn't read-only runs
    only if the founder approved execution for the mission AND Orca's execution policy allows it."""
    if employee.permission_mode == "read_only":
        return PermissionPolicy("read_only")
    mode = "smart" if employee.permission_mode == "auto" else employee.permission_mode

    def approver(call: ToolCall) -> bool:
        if call.name == "write_file":
            return allow_writes
        if call.name == "run_command":
            command = str(call.arguments.get("command") or "")
            return allow_execution and check_command_allowed(command, workspace_root)[0]
        return False

    return PermissionPolicy(mode, approver=approver)


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
                 max_turns: int = DEFAULT_MAX_TURNS) -> EmployeeResult:
    sink: Dict[str, Any] = {}
    tools = ToolRegistry(build_workspace_tools(workspace_root))
    tools.register(_final_output_tool(output_schema, sink))
    execution_note = ("Code execution IS approved for this mission: you may run commands in the workspace."
                      if allow_execution else
                      "Code execution is NOT approved: do not run the application, its tests or interpreters.")
    loop = AgentLoop(
        chat=chat, tools=tools, workspace_root=workspace_root,
        system_prompt=employee.role_prompt + "\n\n" + execution_note,
        permissions=permissions_for(employee, allow_writes=allow_writes, allow_execution=allow_execution,
                                    workspace_root=workspace_root),
        config=AgentLoopConfig(max_turns=max_turns),
    )
    run = loop.run(assignment)
    if run.status == "completed" and "value" not in sink:
        run = loop.resume(run.messages + [user_message(NUDGE)])
    return EmployeeResult(sink.get("value"), run)
