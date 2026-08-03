from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from app.platform.services.agent_execution_bridge_service import execute_agent_via_bridge
from app.platform.services.agent_workflow_context import build_step_workflow_context
from app.platform.services.agent_workflow_steps import block_step, dependency_failed_or_blocked, select_agent_for_step
from app.platform.services.workflow_step_approval_service import create_step_approval_request


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
    scoping_request_id: Optional[str] = None,
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
    handler_result = bridge_result.get("handler_result") or {}
    decision = handler_result.get("decision")
    retried = False
    if decision == "redirect":
        # Exactly one bounded automatic retry, per the decision spec: "the team can
        # act on redirect_instructions without another human". If this retry isn't a
        # clean approve, the retry budget is spent - escalate rather than looping.
        retried = True
        bridge_result = execute_agent_via_bridge(
            db,
            workflow_run_id=workflow_run_id,
            step_run=step_run,
            workflow_context=workflow_context,
            safe_mode=True,
            log_event=log_event,
            prior_redirect_instructions=handler_result.get("redirect_instructions"),
        )
        handler_result = bridge_result.get("handler_result") or {}
        decision = handler_result.get("decision")

    if bridge_result.get("success"):
        step_run["status"] = "completed"
        step_run["output"] = {"mode": "bridge", "bridge_result": bridge_result}
        step_run["error"] = None
    elif decision == "escalate" or retried:
        step_run["status"] = "escalated"
        step_run["output"] = None
        step_run["error"] = {"reason": "escalated", "bridge_result": bridge_result}
        approval = create_step_approval_request(
            db,
            workflow_run_id=workflow_run_id,
            step_run=step_run,
            handler_result=handler_result,
            scoping_request_id=scoping_request_id,
        )
        step_run["approval_id"] = approval.get("approval_id")
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
    # Checked before blocked/failed: an escalation is actionable-pending (a real founder
    # decision resumes it), not a terminal dead end the way blocked/failed are.
    if any(status == "escalated" for status in statuses):
        return "escalated"
    if any(status == "blocked" for status in statuses):
        return "blocked"
    if any(status == "failed" for status in statuses):
        return "failed"
    return "unknown"
