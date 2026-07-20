"""
Command runner — executes approved commands inside the durable workspace.

Captures stdout, stderr, exit code, duration, and timeout.
Blocks shell injection. Uses allowlisted command forms with argv arrays.
"""
from __future__ import annotations

import subprocess
from time import monotonic
from typing import Any, Dict, List, Optional

from app.platform.coding_agent.models import CommandResult
from app.platform.coding_agent.policy import (
    ALLOW_NETWORK_IN_COMMANDS,
    MAX_COMMAND_RUNTIME_SECONDS,
    MAX_STDOUT_CHARS,
    MAX_STDERR_CHARS,
    UNSAFE_METACHARS,
)


# Allowed command prefixes — only these forms execute
ALLOWED_COMMAND_PREFIXES: List[List[str]] = [
    ["python3", "-m", "compileall"],
    ["python3", "-m", "app"],
    ["python3", "-m", "pytest"],
    ["python3", "-c"],
    ["git", "diff", "--check"],
    ["git", "status", "--porcelain"],
    ["git", "diff"],
    ["git", "log"],
    ["git", "rev-parse"],
    ["bash"],
]


def run_command(
    argv: List[str],
    workspace_path: str,
    *,
    timeout_seconds: Optional[int] = None,
) -> CommandResult:
    """
    Execute an approved command inside the workspace.

    Args:
        argv: Command as an argv array, e.g. ["python3", "-m", "compileall", "app"]
        workspace_path: Absolute path to the workspace root.
        timeout_seconds: Override for command timeout.

    Returns:
        CommandResult with exit code, stdout/stderr, duration, and timeout flag.
    """
    timeout = min(timeout_seconds or MAX_COMMAND_RUNTIME_SECONDS, MAX_COMMAND_RUNTIME_SECONDS) if timeout_seconds else MAX_COMMAND_RUNTIME_SECONDS

    validated = _validate_argv(argv)
    if validated is not None:
        return CommandResult(
            argv=argv,
            exit_code=-1,
            stdout="",
            stderr="",
            duration_ms=0,
            error=validated,
        )

    tick = monotonic()
    try:
        completed = subprocess.run(
            argv,
            cwd=workspace_path,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        duration_ms = int((monotonic() - tick) * 1000)
        return CommandResult(
            argv=argv,
            exit_code=completed.returncode,
            stdout=completed.stdout[-MAX_STDOUT_CHARS:] if completed.stdout else "",
            stderr=completed.stderr[-MAX_STDERR_CHARS:] if completed.stderr else "",
            duration_ms=duration_ms,
            timed_out=False,
        )
    except subprocess.TimeoutExpired:
        duration_ms = int((monotonic() - tick) * 1000)
        return CommandResult(
            argv=argv,
            exit_code=-1,
            stdout="",
            stderr="Command timed out after %d seconds." % timeout,
            duration_ms=duration_ms,
            timed_out=True,
            error="Command timed out after %d seconds." % timeout,
        )
    except (OSError, PermissionError) as exc:
        duration_ms = int((monotonic() - tick) * 1000)
        return CommandResult(
            argv=argv,
            exit_code=-1,
            stdout="",
            stderr=str(exc),
            duration_ms=duration_ms,
            error="Command execution failed: %s" % exc,
        )


def run_python_syntax_check(workspace_path: str) -> CommandResult:
    """Run Python 3.9 compileall check in the workspace."""
    return run_command(
        argv=["python3", "-m", "compileall", "-q", "app"],
        workspace_path=workspace_path,
    )


def run_git_diff_check(workspace_path: str) -> CommandResult:
    """Run git diff --check in the workspace."""
    return run_command(
        argv=["git", "diff", "--check"],
        workspace_path=workspace_path,
    )


def _validate_argv(argv: List[str]) -> Optional[str]:
    """Validate command argv for safety. Returns error string or None."""
    if not argv:
        return "Empty command argv."

    if not isinstance(argv, list):
        return "Command argv must be a list."

    if not all(isinstance(arg, str) for arg in argv):
        return "All argv elements must be strings."

    # Check for unsafe metacharacters in the command executable (first arg only).
    # Arguments are passed directly by subprocess without shell interpretation.
    # Exception: -c arguments contain Python code with parens etc — skip those.
    for i, arg in enumerate(argv):
        if i == 0:
            # Only check the executable path for metacharacters
            if any(ch in arg for ch in UNSAFE_METACHARS):
                return "Unsafe shell metacharacter in command executable: %s" % arg
        else:
            # For arguments, only check truly dangerous shell chars (;, |, &, backtick, $, newline)
            dangerous = ";&|`$\n"
            if any(ch in arg for ch in dangerous):
                return "Unsafe shell metacharacter in command argument: %s" % arg

    # Check against allowlisted prefixes
    allowed = False
    for prefix in ALLOWED_COMMAND_PREFIXES:
        if len(argv) >= len(prefix) and argv[:len(prefix)] == prefix:
            allowed = True
            break

    if not allowed:
        return "Command prefix is not in the allowed list: %s" % " ".join(argv[:2])

    # Block network-using commands unless explicitly authorized
    if not ALLOW_NETWORK_IN_COMMANDS:
        network_indicators = ["pip", "curl", "wget", "apt", "brew"]
        joined = " ".join(argv).lower()
        if any(indicator in joined for indicator in network_indicators):
            return "Network-using command blocked: %s" % argv[0]

    return None
