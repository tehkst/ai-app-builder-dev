from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.services.agent_execution_planner_service import build_agent_execution_plan
from app.platform.services.agent_workflow_results import build_workflow_result, finalize_result
from app.platform.services.agent_workflow_steps import create_step_runs
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail


def resume_agent_workflow(
    db: Session,
    *,
    workflow_run_id: str,
    steps: List[Dict[str, Any]],
    decision: Dict[str, Any],
    workflow_name: str = "Agent Workflow",
    simulation: bool = True,
    log_event: bool = True,
    persist_result: bool = True,
    on_step_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
    scoping_request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Continue a workflow run that paused on an escalated step, instead of restarting it.

    `steps` must be the same workflow definition used for the original run (regenerated
    via generate_app_build_workflow the same way a fresh build does - deterministic given
    the same stored scope, so it produces the same step_ids). Already-completed steps are
    pre-seeded as "completed" from their persisted rows (with their ORIGINAL step_run_id,
    not a freshly-minted one - critical, since persist_workflow_result upserts by
    step_run_id, and re-minting it would create a duplicate row instead of updating the
    real one) so `_execute_plan_steps` skips re-running them; the step named in `decision`
    is resolved by the founder's approve/reject rather than by a bridge call. Everything
    else runs through the exact same shared step-execution/finalize path as a fresh run.

    `decision` shape: {"step_id": <the escalated step>, "action": "approve"|"reject",
    "note": <optional founder note>}.
    """
    plan = build_agent_execution_plan(db, steps=steps, log_event=False)
    step_runs = create_step_runs(plan)

    detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
    persisted_by_step_id = {row["step_id"]: row for row in (detail.get("steps") or [])}
    decided_step_id = decision.get("step_id")
    decided_action = decision.get("action")

    for step_id, step_run in step_runs.items():
        prior = persisted_by_step_id.get(step_id)
        if not prior:
            continue
        if step_id == decided_step_id and prior.get("status") == "escalated":
            step_run["step_run_id"] = prior.get("step_run_id") or step_run["step_run_id"]
            if decided_action == "approve":
                step_run["status"] = "completed"
                step_run["output"] = {
                    "mode": "bridge",
                    "bridge_result": {"success": True, "handler_result": prior.get("handler_result") or {}},
                    "founder_decision": {"action": "approve", "note": decision.get("note")},
                }
                step_run["error"] = None
            else:
                step_run["status"] = "failed"
                step_run["output"] = None
                step_run["error"] = {"reason": "founder_rejected", "decision_note": decision.get("note")}
        elif prior.get("status") == "completed":
            step_run["step_run_id"] = prior.get("step_run_id") or step_run["step_run_id"]
            step_run["status"] = "completed"
            step_run["output"] = {
                "mode": "bridge",
                "bridge_result": {"success": True, "handler_result": prior.get("handler_result") or {}},
            }
            step_run["error"] = None

    workflow_status = _execute_plan_steps(
        db,
        plan=plan,
        step_runs=step_runs,
        workflow_run_id=workflow_run_id,
        workflow_name=workflow_name,
        simulation=simulation,
        log_event=log_event,
        on_step_complete=on_step_complete,
        scoping_request_id=scoping_request_id,
    )
    result = build_workflow_result(
        workflow_run_id=workflow_run_id,
        workflow_name=workflow_name,
        workflow_status=workflow_status,
        simulation=simulation,
        plan=plan,
        step_runs=step_runs,
    )
    finalize_result(db, result, log_event=log_event, persist_result=persist_result)
    return result
