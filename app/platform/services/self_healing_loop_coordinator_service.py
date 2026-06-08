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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_flags(*, rerun_attempted: bool = False) -> Dict[str, bool]:
    return {
        "self_healing_loop_coordinator_checked": True,
        "approval_gates_preserved": True,
        "runtime_logs_checked": True,
        "failure_analysis_checked": True,
        "repair_plan_checked": True,
        "repair_approval_status_checked": True,
        "repair_execution_history_checked": True,
        "repair_rerun_history_checked": True,
        "rerun_after_repair_attempted": rerun_attempted,
        "auto_approval_performed": False,
        "unapproved_repair_applied": False,
        "repair_applied_by_loop": False,
        "restore_executed": False,
        "module_rollout_performed": False,
        "install_packages_performed": False,
        "python_command_executed": False,
        "preview_server_started": False,
    }


def _latest_applied_repair(repair_execution_history: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    history = repair_execution_history.get("history") or []
    for record in reversed(history):
        if record.get("applied") is True and record.get("execution_status") == "applied":
            return record
    return None


def _latest_rerun(rerun_history: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    history = rerun_history.get("history") or []
    return history[-1] if history else None


def _determine_loop_status(
    *,
    runtime_status: Dict[str, Any],
    failure_analysis: Dict[str, Any],
    repair_plan_result: Dict[str, Any],
    repair_approval_status: Dict[str, Any],
    repair_execution_history: Dict[str, Any],
    repair_rerun_history: Dict[str, Any],
) -> Dict[str, Any]:
    classification = (failure_analysis.get("classification") or {}).get("category")
    repair_plan = repair_plan_result.get("repair_plan") or {}
    latest_repair = _latest_applied_repair(repair_execution_history)
    latest_rerun = _latest_rerun(repair_rerun_history)

    if classification in {"none_detected"}:
        return {
            "loop_status": "healthy_no_repair_needed",
            "next_required_action": "none",
            "summary": "Runtime analysis found no known failure signature.",
        }

    if not repair_plan.get("plan_needed"):
        return {
            "loop_status": "no_repair_plan_needed",
            "next_required_action": "manual_review_runtime_logs",
            "summary": "No repair plan is needed or logs are unavailable.",
        }

    if not repair_approval_status.get("approved"):
        return {
            "loop_status": "waiting_for_repair_approval",
            "next_required_action": "approve_or_reject_repair_plan",
            "summary": "Repair plan exists but has not been approved.",
        }

    if latest_repair is None:
        return {
            "loop_status": "waiting_for_approved_repair_execution",
            "next_required_action": "execute_approved_repair",
            "summary": "Repair is approved, but no successful repair execution has been recorded.",
        }

    if latest_rerun is None:
        return {
            "loop_status": "waiting_for_repair_rerun",
            "next_required_action": "start_rerun_after_repair",
            "summary": "Repair execution exists, but no repair re-run has been recorded.",
        }

    if latest_rerun.get("rerun_started") is True:
        return {
            "loop_status": "self_healing_loop_completed",
            "next_required_action": "review_rerun_result",
            "summary": "Repair was applied and re-run was started through the approved runtime path.",
        }

    return {
        "loop_status": "repair_rerun_blocked_or_failed",
        "next_required_action": "review_repair_rerun_block_reason",
        "summary": "Repair re-run history exists, but the re-run did not start successfully.",
    }


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
        "history": _SELF_HEALING_LOOP_HISTORY.get(workflow_run_id, []),
        "safety_flags": _safe_flags(rerun_attempted=False),
    }


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
