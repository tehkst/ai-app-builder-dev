from __future__ import annotations

import uuid
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.platform.services.agent_execution_bridge_service import execute_agent_via_bridge
from app.platform.services.agent_execution_planner_service import build_agent_execution_plan
from app.platform.services.agent_workflow_context import build_step_workflow_context
from app.platform.services.agent_workflow_results import build_workflow_result, finalize_result
from app.platform.services.agent_workflow_scalability import (
    build_blocked_scalability_result,
    validate_workflow_scalability,
)
from app.platform.services.agent_workflow_steps import (
    block_step,
    complete_step_simulation,
    create_step_runs,
    dependencies_completed,
    dependency_failed_or_blocked,
    select_agent_for_step,
)


def execute_agent_workflow(
    db: Session,
    *,
    steps: List[Dict[str, Any]],
    workflow_name: str = "Agent Workflow",
    simulation: bool = True,
    log_event: bool = True,
    persist_result: bool = True,
) -> Dict[str, Any]:
    workflow_run_id = f"workflow_run_{uuid.uuid4().hex}"
    scalability_violations = validate_workflow_scalability(steps)
    if scalability_violations:
        result = build_blocked_scalability_result(
            workflow_run_id=workflow_run_id,
            workflow_name=workflow_name,
            simulation=simulation,
            steps=steps,
            violations=scalability_violations,
        )
        finalize_result(db, result, log_event=log_event, persist_result=persist_result)
        return result

    plan = build_agent_execution_plan(db, steps=steps, log_event=False)
    step_runs = create_step_runs(plan)
    workflow_status = _execute_plan_steps(
        db,
        plan=plan,
        step_runs=step_runs,
        workflow_run_id=workflow_run_id,
        workflow_name=workflow_name,
        simulation=simulation,
        log_event=log_event,
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


def _execute_plan_steps(
    db: Session,
    *,
    plan: Dict[str, Any],
    step_runs: Dict[str, Dict[str, Any]],
    workflow_run_id: str,
    workflow_name: str,
    simulation: bool,
    log_event: bool,
) -> str:
    if plan.get("validation_issues"):
        for step_run in step_runs.values():
            block_step(step_run, reason="invalid_plan")
        return "invalid_plan"
    if plan.get("has_cycle"):
        for step_run in step_runs.values():
            block_step(step_run, reason="dependency_cycle_detected")
        return "dependency_cycle_detected"

    _run_ready_steps(db, plan, step_runs, workflow_run_id, workflow_name, simulation, log_event)
    _block_unreachable_steps(step_runs)
    return _workflow_status(step_runs)


def _run_ready_steps(
    db: Session,
    plan: Dict[str, Any],
    step_runs: Dict[str, Dict[str, Any]],
    workflow_run_id: str,
    workflow_name: str,
    simulation: bool,
    log_event: bool,
) -> None:
    progress_made = True
    while progress_made:
        progress_made = False
        for step_id in plan.get("execution_order", []):
            step_run = step_runs.get(step_id)
            if not step_run or step_run.get("status") != "queued":
                continue
            if _block_if_not_ready(step_run, step_runs):
                progress_made = True
                continue
            if simulation:
                complete_step_simulation(step_run)
            else:
                _run_step_via_bridge(db, workflow_run_id, workflow_name, step_run, step_runs, log_event)
            progress_made = True


def _block_if_not_ready(step_run: Dict[str, Any], step_runs: Dict[str, Dict[str, Any]]) -> bool:
    if dependency_failed_or_blocked(step_run, step_runs):
        block_step(step_run, reason="dependency_failed_or_blocked")
        return True
    if not dependencies_completed(step_run, step_runs):
        return True
    if not step_run.get("agent_available"):
        block_step(step_run, reason="missing_required_capability")
        return True
    return False


def _run_step_via_bridge(
    db: Session,
    workflow_run_id: str,
    workflow_name: str,
    step_run: Dict[str, Any],
    step_runs: Dict[str, Dict[str, Any]],
    log_event: bool,
) -> None:
    select_agent_for_step(step_run)
    step_run["status"] = "running"
    workflow_context = build_step_workflow_context(
        workflow_name=workflow_name,
        step_run=step_run,
        step_runs=step_runs,
    )
    step_run["workflow_context"] = workflow_context
    bridge_result = execute_agent_via_bridge(
        db,
        workflow_run_id=workflow_run_id,
        step_run=step_run,
        workflow_context=workflow_context,
        safe_mode=True,
        log_event=log_event,
    )
    if bridge_result.get("success"):
        step_run["status"] = "completed"
        step_run["output"] = {"mode": "bridge", "bridge_result": bridge_result}
        step_run["error"] = None
    else:
        step_run["status"] = "failed"
        step_run["output"] = None
        step_run["error"] = {"reason": bridge_result.get("status") or "bridge_execution_failed", "bridge_result": bridge_result}


def _block_unreachable_steps(step_runs: Dict[str, Dict[str, Any]]) -> None:
    for step_run in step_runs.values():
        if step_run.get("status") != "queued":
            continue
        reason = "dependency_failed_or_blocked" if dependency_failed_or_blocked(step_run, step_runs) else "not_reachable"
        block_step(step_run, reason=reason)


def _workflow_status(step_runs: Dict[str, Dict[str, Any]]) -> str:
    statuses = [step_run.get("status") for step_run in step_runs.values()]
    if all(status == "completed" for status in statuses):
        return "completed"
    if any(status == "blocked" for status in statuses):
        return "blocked"
    if any(status == "failed" for status in statuses):
        return "failed"
    return "unknown"

