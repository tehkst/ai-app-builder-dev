"""Permission policy for agent tool calls (modelled on goose's permission judge).

Read-only tools always run. Everything else depends on the mode:

- ``auto``: run everything (only for trusted, sandboxed workspaces).
- ``smart``: run commands recognised as read-only (deterministic allowlist first, then an
  optional LLM judge); route the rest to the approver.
- ``approve``: route every non-read-only call to the approver.
- ``read_only``: deny every non-read-only call.

With no approver configured, routed calls are denied, so founder-gated actions stay gated
by default.
"""
from __future__ import annotations

import re

import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from app.platform.nautilus.messages import ToolCall
from app.platform.nautilus.tools import Tool

PERMISSION_MODES = ("auto", "smart", "approve", "read_only")

READ_ONLY_COMMANDS = {
    "ls", "cat", "head", "tail", "wc", "pwd", "find", "grep", "tree", "file", "stat", "du",
    "diff", "echo",
}
# `git branch` is excluded on purpose (`-D` deletes); `--output` lets diff/log write files.
READ_ONLY_SUBCOMMANDS = {
    "git": {"status", "diff", "log", "show", "ls-files", "blame", "rev-parse"},
    "npm": {"ls", "outdated", "view"},
    "pip": {"list", "show", "freeze"},
}
# find is allowlisted rather than denylisted: its actions (-delete, -exec*, -ok*, -fprint*,
# -fls, ...) can write or execute, and any option not listed here routes to the approver.
SAFE_FIND_ARGS = {
    "-name", "-iname", "-path", "-ipath", "-regex", "-iregex", "-type", "-maxdepth", "-mindepth",
    "-size", "-mtime", "-mmin", "-newer", "-empty", "-print", "-print0", "-not", "!", "(", ")",
    "-o", "-a", "-or", "-and",
}

SED_PRINT = re.compile(r"(?:\d+|\$)(?:,(?:\d+|\$))?p")

Approver = Callable[[ToolCall], bool]
Judge = Callable[[str], Optional[bool]]  # command -> True (read-only), False, or None (unsure)


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str


def _operand_confined(value: str, root: Optional[Path]) -> bool:
    if not value or value in (".", "./"):
        return True
    if value.startswith(("/", "~")) or ".." in Path(value).parts:
        return False
    if root is None:
        return True
    return (root / value).resolve() == root or root in (root / value).resolve().parents


def operands_confined(args: List[str], workspace_root: Optional[str]) -> bool:
    """True when every argument that could name a file stays inside the workspace.

    Commands start in the workspace, but nothing stops ``cat /proc/1/environ`` or
    ``cat ../../.env``; auto-approval therefore requires all operands (and ``--flag=value``
    values) to be relative, free of ``..``, and - when the workspace is known - to resolve
    (following symlinks) inside it. Non-path operands such as grep patterns pass unless they
    look like an escaping path, in which case the command goes to the approver instead.
    """
    root = Path(workspace_root).resolve() if workspace_root else None
    for arg in args:
        value = arg.split("=", 1)[1] if arg.startswith("-") and "=" in arg else arg
        if value.startswith("-") and value == arg:
            continue
        if not _operand_confined(value, root):
            return False
    return True


def command_is_read_only(command: str, workspace_root: Optional[str] = None) -> bool:
    try:
        argv = shlex.split(command)
    except ValueError:
        return False
    if not argv or not operands_confined(argv[1:], workspace_root):
        return False
    program = argv[0].rsplit("/", 1)[-1]
    if any(arg.startswith("--output") for arg in argv[1:]):
        return False
    if program == "find":
        return all(arg in SAFE_FIND_ARGS for arg in argv[1:] if arg.startswith("-") or arg in ("!", "(", ")"))
    if program == "sed":  # only `sed -n 'A,Bp' FILE...` (print a line range; no in-place edits or w/e commands)
        return len(argv) >= 4 and argv[1] == "-n" and bool(SED_PRINT.fullmatch(argv[2])) and \
            not any(a.startswith("-") for a in argv[3:])
    if program in READ_ONLY_COMMANDS:
        return True
    subcommands = READ_ONLY_SUBCOMMANDS.get(program)
    return bool(subcommands and len(argv) > 1 and argv[1] in subcommands)


class PermissionPolicy:
    def __init__(self, mode: str = "approve", approver: Optional[Approver] = None, judge: Optional[Judge] = None,
                 workspace_root: Optional[str] = None) -> None:
        if mode not in PERMISSION_MODES:
            raise ValueError(f"Unknown permission mode '{mode}'. Use one of {PERMISSION_MODES}.")
        self.mode = mode
        self.approver = approver
        self.judge = judge
        self.workspace_root = workspace_root

    def decide(self, tool: Tool, call: ToolCall) -> PermissionDecision:
        if tool.read_only:
            return PermissionDecision(True, "read-only tool")
        if self.mode == "auto":
            return PermissionDecision(True, "auto mode")
        if self.mode == "read_only":
            return PermissionDecision(False, "this agent is restricted to read-only tools")
        if self.mode == "smart" and tool.name == "run_command":
            command = str(call.arguments.get("command") or "")
            if command_is_read_only(command, self.workspace_root):
                return PermissionDecision(True, "command recognised as read-only")
            # The judge only rules on read-only-ness; it never overrides workspace confinement.
            if self.judge is not None and self._confined(command) and self._judge_says_read_only(command):
                return PermissionDecision(True, "judge classified command as read-only")
        return self._ask(call)

    def _confined(self, command: str) -> bool:
        try:
            return operands_confined(shlex.split(command)[1:], self.workspace_root)
        except ValueError:
            return False

    def _judge_says_read_only(self, command: str) -> bool:
        try:
            return self.judge(command) is True
        except Exception:
            return False

    def _ask(self, call: ToolCall) -> PermissionDecision:
        if self.approver is None:
            return PermissionDecision(False, "requires approval and no approver is configured")
        try:
            approved = bool(self.approver(call))
        except Exception as exc:
            return PermissionDecision(False, f"approver failed: {exc}")
        return PermissionDecision(approved, "approved" if approved else "declined by approver")


def build_llm_judge(complete: Callable[[str, str], str]) -> Judge:
    """Wrap a text-completion function (system, prompt) -> text as a read-only judge."""
    system = (
        "You classify shell commands. Reply with exactly one word: READ_ONLY if the command "
        "only inspects state and cannot modify files, processes, network resources or "
        "installed software; otherwise WRITE."
    )

    def judge(command: str) -> Optional[bool]:
        answer = complete(system, f"Command: {command}").strip().upper()
        if answer.startswith("READ_ONLY"):
            return True
        if answer.startswith("WRITE"):
            return False
        return None

    return judge
