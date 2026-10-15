# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.platform.services.controlled_sandbox_runtime_service import (
    get_controlled_sandbox_runtime_logs,
    get_controlled_sandbox_runtime_status,
)
from app.platform.services.repair_approval_gate_service import get_repair_approval_status
from app.platform.services.repair_executor_service import get_repair_execution_history
from app.platform.services.repair_plan_generator_service import generate_repair_plan_for_workflow
from app.platform.services.repair_rerun_coordinator_service import (
    get_repair_rerun_history,
    rerun_after_successful_repair,
)
from app.platform.services.runtime_failure_analyzer_service import analyze_runtime_failure_for_workflow
SELF_HEALING_LOOP_COORDINATOR_SAFETY_MODE = "self_healing_loop_coordinator_v77_approval_preserving"
_SELF_HEALING_LOOP_HISTORY: Dict[str, List[Dict[str, Any]]] = {}

def inspect_self_healing_loop(
    *,
    workflow_run_id: str,
) -> Dict[str, Any]:
    runtime_status = get_controlled_sandbox_runtime_status(workflow_run_id)
    runtime_logs = get_controlled_sandbox_runtime_logs(workflow_run_id)
    failure_analysis = analyze_runtime_failure_for_workflow(workflow_run_id)
    repair_plan_result = generate_repair_plan_for_workflow(workflow_run_id)
    repair_approval_status = get_repair_approval_status(workflow_run_id)
    repair_execution_history = get_repair_execution_history(workflow_run_id)
    repair_rerun_history = get_repair_rerun_history(workflow_run_id)
    outcome = _determine_loop_status(
        runtime_status=runtime_status,
        failure_analysis=failure_analysis,
        repair_plan_result=repair_plan_result,
        repair_approval_status=repair_approval_status,
        repair_execution_history=repair_execution_history,
        repair_rerun_history=repair_rerun_history,
    )

    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": SELF_HEALING_LOOP_COORDINATOR_SAFETY_MODE,
        "loop_status": outcome["loop_status"],
        "next_required_action": outcome["next_required_action"],
        "summary": outcome["summary"],
        "runtime_status": runtime_status,
        "runtime_logs": runtime_logs,
        "failure_analysis": failure_analysis,
        "repair_plan_result": repair_plan_result,
        "repair_approval_status": repair_approval_status,
        "repair_execution_history": repair_execution_history,
        "repair_rerun_history": repair_rerun_history,
        "nautilus_repair_proposal": _nautilus_proposal_summary(workflow_run_id),
        "nautilus_next_step": _nautilus_next_step(outcome["loop_status"], workflow_run_id),
        "history": _SELF_HEALING_LOOP_HISTORY.get(workflow_run_id, []),
        "safety_flags": _safe_flags(rerun_attempted=False),
    }


def _nautilus_proposal_summary(workflow_run_id: str) -> Optional[Dict[str, Any]]:
    from app.platform.services.nautilus_repair_service import latest_nautilus_proposal

    proposal = latest_nautilus_proposal(workflow_run_id)
    if proposal is None:
        return None
    return {key: proposal.get(key) for key in ("proposal_id", "proposal_status", "created_at", "explanation")} | {
        "changed_files": [change["path"] for change in proposal.get("changes") or []],
    }


def _nautilus_next_step(loop_status: str, workflow_run_id: str) -> Optional[str]:
    """Where Nautilus can move the loop forward; None when it has nothing to add."""
    if loop_status not in {"waiting_for_repair_approval", "waiting_for_approved_repair_execution"}:
        return None
    from app.platform.services.nautilus_repair_service import latest_nautilus_proposal

    proposal = latest_nautilus_proposal(workflow_run_id)
    if proposal is None or proposal.get("proposal_status") != "proposed":
        return "generate_nautilus_repair_proposal"
    if loop_status == "waiting_for_repair_approval":
        return "review_nautilus_proposal_and_approve_repair_plan"
    return "apply_nautilus_repair_proposal"

def run_self_healing_loop_once(
    *,
    db: Session,
    workflow_run_id: str,
    requested_by: str = "platform_admin",
) -> Dict[str, Any]:
    before = inspect_self_healing_loop(workflow_run_id=workflow_run_id)
    rerun_result = None
    rerun_attempted = False

    if before.get("loop_status") == "waiting_for_repair_rerun":
        rerun_attempted = True
        rerun_result = rerun_after_successful_repair(
            db=db,
            workflow_run_id=workflow_run_id,
            requested_by=requested_by,
            perform_install=False,
        )

    after = inspect_self_healing_loop(workflow_run_id=workflow_run_id)
    record = {
        "workflow_run_id": workflow_run_id,
        "created_at": _now_iso(),
        "requested_by": requested_by,
        "before_loop_status": before.get("loop_status"),
        "after_loop_status": after.get("loop_status"),
        "before_next_required_action": before.get("next_required_action"),
        "after_next_required_action": after.get("next_required_action"),
        "rerun_attempted": rerun_attempted,
        "rerun_started": bool(rerun_result and rerun_result.get("rerun_started")),
    }
    _SELF_HEALING_LOOP_HISTORY.setdefault(workflow_run_id, []).append(record)

    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": SELF_HEALING_LOOP_COORDINATOR_SAFETY_MODE,
        "loop_status": after.get("loop_status"),
        "next_required_action": after.get("next_required_action"),
        "before": before,
        "rerun_result": rerun_result,
        "after": after,
        "history": _SELF_HEALING_LOOP_HISTORY.get(workflow_run_id, []),
        "safety_flags": _safe_flags(rerun_attempted=rerun_attempted),
    }

def get_self_healing_loop_history(workflow_run_id: str) -> Dict[str, Any]:
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": SELF_HEALING_LOOP_COORDINATOR_SAFETY_MODE,
        "history": _SELF_HEALING_LOOP_HISTORY.get(workflow_run_id, []),
        "safety_flags": _safe_flags(rerun_attempted=False),
    }

def reset_self_healing_loop_history_for_check() -> None:
    _SELF_HEALING_LOOP_HISTORY.clear()
