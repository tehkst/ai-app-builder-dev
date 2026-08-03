from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List, Optional

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
    on_step_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
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

    _run_ready_steps(db, plan, step_runs, workflow_run_id, workflow_name, simulation, log_event, on_step_complete)
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
                _run_step_via_bridge(db, workflow_run_id, workflow_name, step_run, step_runs, log_event)
            progress_made = True
            _emit_step_event(on_step_complete, step_run)


def _emit_step_event(on_step_complete: Optional[Callable[[Dict[str, Any]], None]], step_run: Dict[str, Any]) -> None:
    if not on_step_complete:
        return
    on_step_complete({
        "type": "step_completed",
        "step_id": step_run.get("step_id"),
        "title": step_run.get("title"),
        "status": step_run.get("status"),
        "message": step_thought_message(step_run),
    })


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


def step_thought_message(step_run: Dict[str, Any]) -> Optional[str]:
    """Best-effort real reasoning text for a step, once it has run.

    Reads whichever of output/error the executor actually populated (success ->
    output.bridge_result.handler_result, failure -> error.bridge_result.handler_result)
    and surfaces the management agent's real message/rationale - never a fabricated
    "thinking..." placeholder. Returns None when nothing real is available yet.
    """
    source = step_run.get("output") if step_run.get("status") == "completed" else step_run.get("error")
    handler_result = {}
    if isinstance(source, dict):
        bridge_result = source.get("bridge_result")
        if isinstance(bridge_result, dict):
            handler_result = bridge_result.get("handler_result") or {}
    if isinstance(handler_result, dict):
        # "message" is a terse status label ("CEO decision: approve."); "rationale" is
        # the actual reasoning behind it. Combine both when present so the stream reads
        # as a real thought, not just a verdict - and fall back to whichever exists alone.
        message = handler_result.get("message")
        rationale = handler_result.get("rationale")
        if message and rationale:
            return f"{message} {rationale}"
        if message or rationale:
            return str(message or rationale)
    if isinstance(source, dict) and source.get("message"):
        return str(source["message"])
    error = step_run.get("error")
    if isinstance(error, dict) and error.get("error"):
        return str(error["error"])
    if isinstance(error, dict) and error.get("reason"):
        return str(error["reason"]).replace("_", " ")
    return None


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


def _block_unreachable_steps(
    step_runs: Dict[str, Dict[str, Any]],
    on_step_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> None:
    for step_run in step_runs.values():
        if step_run.get("status") != "queued":
            continue
        reason = "dependency_failed_or_blocked" if dependency_failed_or_blocked(step_run, step_runs) else "not_reachable"
        block_step(step_run, reason=reason)
        _emit_step_event(on_step_complete, step_run)


def _workflow_status(step_runs: Dict[str, Dict[str, Any]]) -> str:
    statuses = [step_run.get("status") for step_run in step_runs.values()]
    if all(status == "completed" for status in statuses):
        return "completed"
    if any(status == "blocked" for status in statuses):
        return "blocked"
    if any(status == "failed" for status in statuses):
        return "failed"
    return "unknown"

