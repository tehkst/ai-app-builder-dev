"""Orca's quality gates: acceptance checks (only with the founder's execution approval) and the
final integration gate. In client missions a check that failed only because the sandbox lacks a
database or the internet is marked `not_run` (it says nothing about the code): it doesn't fail the
task, and the mission then finishes unverified with those checks named."""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from app.platform.nautilus.workspace_tools import run_workspace_command
from app.platform.orca.execution_policy import check_command_allowed
from app.platform.orca.handoffs import CHECK_OUTPUT_CHARS
from app.platform.orca.models import Mission
from app.platform.orca.sandbox_commands import needs_outside_service, run_sandboxed

CHECK_TIMEOUT_SECONDS = 300


def run_checks(mission: Mission, commands: List[str], lock: Optional[threading.Lock] = None) -> List[Dict[str, Any]]:
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
            if lock is not None:  # parallel tasks share the workspace: one command at a time
                with lock:
                    outcome = run(mission.workspace_root, command, CHECK_TIMEOUT_SECONDS)
            else:
                outcome = run(mission.workspace_root, command, CHECK_TIMEOUT_SECONDS)
        except Exception as exc:  # e.g. an unparseable command: a failed check, never a crash
            outcome = {"exit_code": None, "output": f"Could not run check: {exc}"}
        result = {"command": command, "passed": outcome["exit_code"] == 0,
                  "exit_code": outcome["exit_code"], "output": outcome["output"][-CHECK_OUTPUT_CHARS:]}
        needed = needs_outside_service(outcome["output"]) if mission.sandboxed and not result["passed"] else None
        if needed:
            result["not_run"] = needed
        results.append(result)
    return results


def checks_ok(results: List[Dict[str, Any]]) -> bool:
    """Every check passed or couldn't run here, and (if any ran) at least one really passed."""
    return all(r["passed"] or r.get("not_run") for r in results) and (not results or any(r["passed"] for r in results))


def outcome_word(result: Dict[str, Any]) -> str:
    if result["passed"]:
        return "passed"
    return f"couldn't run here (needs {result['not_run']})" if result.get("not_run") else "failed"


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
    not_run = [{"command": r["command"], "needs": r["not_run"]} for r in results if r.get("not_run")]
    mission.integration = {"check_results": results, "passed": checks_ok(results), "not_run": not_run}
    if mission.integration["passed"] and not_run:
        mission.status = "complete_unverified"  # the founder must run these where the services exist
        mission.record("completed", verified=False, reason="some checks need what the sandbox doesn't have",
                       not_run=[n["command"] for n in not_run])
    elif mission.integration["passed"]:
        mission.status = "complete"
        mission.record("completed", verified=True, checks=len(results))
    else:
        mission.status = "escalated"
        mission.escalation = {"reason": "Integration gate failed: a previously passing check now fails.",
                              "check_results": results}
        mission.record("escalated", stage="integration")
