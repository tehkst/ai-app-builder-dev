# Split from the legacy single-file module to keep each file under 200 lines (this repo's
# own convention). Shared names cross the part boundary via the package __init__.py's
# namespace merge - see that file's docstring and agent_execution_bridge_service/__init__.py
# for the established pattern this follows.
from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.services.agent_execution_planner_service import build_agent_execution_plan
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
)


def execute_agent_workflow(
    db: Session,
    *,
    steps: List[Dict[str, Any]],
    workflow_name: str = "Agent Workflow",
    simulation: bool = True,
    log_event: bool = True,
    persist_result: bool = True,
    on_step_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
    scoping_request_id: Optional[str] = None,
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


def _execute_plan_steps(
    db: Session,
    *,
    plan: Dict[str, Any],
    step_runs: Dict[str, Dict[str, Any]],
    workflow_run_id: str,
    workflow_name: str,
    simulation: bool,
    log_event: bool,
    on_step_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
    scoping_request_id: Optional[str] = None,
) -> str:
    if plan.get("validation_issues"):
        for step_run in step_runs.values():
            block_step(step_run, reason="invalid_plan")
            _emit_step_event(on_step_complete, step_run)
        return "invalid_plan"
    if plan.get("has_cycle"):
        for step_run in step_runs.values():
            block_step(step_run, reason="dependency_cycle_detected")
            _emit_step_event(on_step_complete, step_run)
        return "dependency_cycle_detected"

    _run_ready_steps(db, plan, step_runs, workflow_run_id, workflow_name, simulation, log_event, on_step_complete, scoping_request_id)
    _block_unreachable_steps(step_runs, on_step_complete)
    return _workflow_status(step_runs)


def _run_ready_steps(
    db: Session,
    plan: Dict[str, Any],
    step_runs: Dict[str, Dict[str, Any]],
    workflow_run_id: str,
    workflow_name: str,
    simulation: bool,
    log_event: bool,
    on_step_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
    scoping_request_id: Optional[str] = None,
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
                _emit_step_event(on_step_complete, step_run)
                continue
            if on_step_complete:
                on_step_complete({"type": "step_started", "step_id": step_run.get("step_id"), "title": step_run.get("title")})
            if simulation:
                complete_step_simulation(step_run)
            else:
                _run_step_via_bridge(db, workflow_run_id, workflow_name, step_run, step_runs, log_event, scoping_request_id)
            progress_made = True
            _emit_step_event(on_step_complete, step_run)


def _emit_step_event(on_step_complete: Optional[Callable[[Dict[str, Any]], None]], step_run: Dict[str, Any]) -> None:
    if not on_step_complete:
        return
    event = {
        "type": "step_completed",
        "step_id": step_run.get("step_id"),
        "title": step_run.get("title"),
        "status": step_run.get("status"),
        "message": step_thought_message(step_run),
    }
    if step_run.get("approval_id"):
        event["approval_id"] = step_run["approval_id"]
    on_step_complete(event)


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
