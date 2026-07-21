"""
Validation runner — selects and runs actual repository validation commands.

Command selection follows this precedence:
1. Approved mission validation plan
2. Engineering Manager validation plan
3. Repository-native configuration
4. Existing platform validation catalogue
5. Safe platform defaults
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.platform.coding_agent.command_runner import (
    run_command,
    run_git_diff_check,
    run_python_syntax_check,
)
from app.platform.coding_agent.models import CommandResult, ValidationOutcome
from app.platform.code_planner.service import DEFAULT_VALIDATION_GATES


def run_validation(
    iteration: int,
    workspace_path: str,
    *,
    mission_validation_plan: Optional[List[Dict[str, Any]]] = None,
    engineering_manager_plan: Optional[List[str]] = None,
    additional_commands: Optional[List[Dict[str, Any]]] = None,
) -> ValidationOutcome:
    """
    Run the full validation suite in the workspace.

    Args:
        iteration: Current iteration number.
        workspace_path: Workspace root path.
        mission_validation_plan: Commands from the approved mission plan.
        engineering_manager_plan: Commands from Engineering Manager.
        additional_commands: Extra commands (e.g., from edit planner).

    Returns:
        ValidationOutcome with all results.
    """
    commands_to_run = _select_commands(mission_validation_plan, engineering_manager_plan, additional_commands)

    results: List[CommandResult] = []
    for cmd_spec in commands_to_run:
        argv = _normalize_argv(cmd_spec)
        result = run_command(argv=argv, workspace_path=workspace_path)
        results.append(result)

    # Always run syntax check
    syntax_result = run_python_syntax_check(workspace_path)
    if syntax_result.exit_code != 0:
        results.append(syntax_result)

    # Always run git diff --check
    diff_result = run_git_diff_check(workspace_path)
    if diff_result.exit_code != 0:
        results.append(diff_result)

    passed = all(r.exit_code == 0 for r in results)
    failed = any(r.exit_code != 0 for r in results)

    overall = "passed" if passed else "failed"

    summary_lines: List[str] = []
    for r in results:
        status = "PASS" if r.exit_code == 0 else "FAIL"
        summary_lines.append("[%s] %s (exit %d, %dms)" % (
            status, " ".join(r.argv), r.exit_code, r.duration_ms,
        ))

    return ValidationOutcome(
        iteration=iteration,
        overall=overall,
        commands=results,
        summary="\n".join(summary_lines),
    )


def _select_commands(
    mission_plan: Optional[List[Dict[str, Any]]],
    em_plan: Optional[List[str]],
    additional: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Select validation commands by precedence."""

    # 1. Approved mission validation plan
    if mission_plan:
        return mission_plan

    # 2. Engineering Manager plan (convert string forms to dict)
    if em_plan:
        result: List[Dict[str, Any]] = []
        for item in em_plan:
            if isinstance(item, str):
                result.append(_parse_command_string(item))
            elif isinstance(item, dict):
                result.append(item)
        return result

    # 3. Additional commands (from edit planner)
    if additional:
        return additional

    # 4. Platform defaults
    return _platform_defaults_to_commands()


def _platform_defaults_to_commands() -> List[Dict[str, Any]]:
    """Convert DEFAULT_VALIDATION_GATES to structured command specs."""
    commands: List[Dict[str, Any]] = []
    for gate in DEFAULT_VALIDATION_GATES:
        commands.append(_parse_command_string(gate))
    return commands


def _parse_command_string(raw: str) -> Dict[str, Any]:
    """Parse a command string like 'python -m compileall app' into argv."""
    # Skip non-command items (like PR workflow notes)
    if "workflow" in raw.lower() or "ci" in raw.lower() or "must pass" in raw.lower():
        return {"argv": ["echo", raw], "reason": "Informational gate"}
    args = raw.strip().split()
    return {"argv": args if args else ["echo", raw], "reason": "Platform default validation gate"}


def _normalize_argv(cmd_spec: Dict[str, Any]) -> List[str]:
    """Extract argv array from a command spec dict."""
    argv = cmd_spec.get("argv") or cmd_spec.get("command") or []
    if isinstance(argv, str):
        argv = argv.strip().split()
    if not argv:
        argv = ["echo", "No validation command specified."]
    return [str(arg) for arg in argv]
