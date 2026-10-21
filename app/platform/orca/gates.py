"""Orca's quality gates: acceptance checks (only with the founder's execution approval) and the
final integration gate."""
from __future__ import annotations

from typing import Any, Dict, List

from app.platform.nautilus.workspace_tools import run_workspace_command
from app.platform.orca.execution_policy import check_command_allowed
from app.platform.orca.handoffs import CHECK_OUTPUT_CHARS
from app.platform.orca.models import Mission
from app.platform.orca.sandbox_commands import run_sandboxed

CHECK_TIMEOUT_SECONDS = 300


def run_checks(mission: Mission, commands: List[str]) -> List[Dict[str, Any]]:
    if not mission.execution_allowed:
        return []
    results = []
    for command in commands:
        allowed, reason = check_command_allowed(command, mission.workspace_root)
        if not allowed:
            results.append({"command": command, "passed": False, "exit_code": None,
                            "output": f"Refused by Orca's execution policy: {reason}"})
            continue
        try:
            run = run_sandboxed if mission.sandboxed else run_workspace_command
            outcome = run(mission.workspace_root, command, CHECK_TIMEOUT_SECONDS)
        except Exception as exc:  # e.g. an unparseable command: a failed check, never a crash
            outcome = {"exit_code": None, "output": f"Could not run check: {exc}"}
        results.append({"command": command, "passed": outcome["exit_code"] == 0,
                        "exit_code": outcome["exit_code"], "output": outcome["output"][-CHECK_OUTPUT_CHARS:]})
    return results


def integrate(mission: Mission) -> None:
    """All tasks passed: re-run every check together (or finish unverified without approval)."""
    if not mission.execution_allowed:
        mission.status = "complete_unverified"
        mission.record("completed", verified=False, reason=f"execution {mission.execution_approval}")
        return
    if not mission.tasks or any(not t.acceptance_checks for t in mission.tasks):
        mission.status = "complete_unverified"  # verification needs a real check for every task
        mission.record("completed", verified=False, reason="a task has no acceptance checks")
        return
    results = run_checks(mission, [c for t in mission.tasks for c in t.acceptance_checks])
    mission.integration = {"check_results": results, "passed": all(r["passed"] for r in results)}
    if mission.integration["passed"]:
        mission.status = "complete"
        mission.record("completed", verified=True, checks=len(results))
    else:
        mission.status = "escalated"
        mission.escalation = {"reason": "Integration gate failed: a previously passing check now fails.",
                              "check_results": results}
        mission.record("escalated", stage="integration")
