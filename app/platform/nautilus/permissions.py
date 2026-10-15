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

import shlex
from dataclasses import dataclass
from typing import Callable, Optional

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
UNSAFE_FIND_FLAGS = {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprintf", "-fls"}

Approver = Callable[[ToolCall], bool]
Judge = Callable[[str], Optional[bool]]  # command -> True (read-only), False, or None (unsure)


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str


def command_is_read_only(command: str) -> bool:
    try:
        argv = shlex.split(command)
    except ValueError:
        return False
    if not argv:
        return False
    program = argv[0].rsplit("/", 1)[-1]
    if any(arg.startswith("--output") for arg in argv[1:]):
        return False
    if program == "find":
        return not any(arg in UNSAFE_FIND_FLAGS for arg in argv[1:])
    if program in READ_ONLY_COMMANDS:
        return True
    subcommands = READ_ONLY_SUBCOMMANDS.get(program)
    return bool(subcommands and len(argv) > 1 and argv[1] in subcommands)


class PermissionPolicy:
    def __init__(self, mode: str = "approve", approver: Optional[Approver] = None, judge: Optional[Judge] = None) -> None:
        if mode not in PERMISSION_MODES:
            raise ValueError(f"Unknown permission mode '{mode}'. Use one of {PERMISSION_MODES}.")
        self.mode = mode
        self.approver = approver
        self.judge = judge

    def decide(self, tool: Tool, call: ToolCall) -> PermissionDecision:
        if tool.read_only:
            return PermissionDecision(True, "read-only tool")
        if self.mode == "auto":
            return PermissionDecision(True, "auto mode")
        if self.mode == "read_only":
            return PermissionDecision(False, "this agent is restricted to read-only tools")
        if self.mode == "smart" and tool.name == "run_command":
            command = str(call.arguments.get("command") or "")
            if command_is_read_only(command):
                return PermissionDecision(True, "command recognised as read-only")
            if self.judge is not None and self._judge_says_read_only(command):
                return PermissionDecision(True, "judge classified command as read-only")
        return self._ask(call)

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
