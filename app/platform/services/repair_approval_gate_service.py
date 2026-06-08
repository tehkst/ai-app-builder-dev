from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.platform.services.repair_plan_generator_service import generate_repair_plan_for_workflow


REPAIR_APPROVAL_GATE_SAFETY_MODE = "repair_approval_gate_v74_approval_only"

_REPAIR_APPROVAL_RECORDS: Dict[str, Dict[str, Any]] = {}
_REPAIR_APPROVAL_HISTORY: Dict[str, List[Dict[str, Any]]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_flags(*, approved: bool = False, blocked: bool = True) -> Dict[str, bool]:
    return {
        "repair_approval_gate_checked": True,
        "repair_approval_recorded": approved,
        "repair_apply_blocked_without_approval": blocked,
        "approval_required_before_apply": True,
        "auto_approval_performed": False,
        "generated_files_written": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "generated_code_execution_performed": False,
        "install_packages_performed": False,
        "node_command_executed": False,
        "python_command_executed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "repair_applied": False,
        "restore_executed": False,
        "module_rollout_performed": False,
    }


def _history_event(workflow_run_id: str, action: str, record: Dict[str, Any]) -> Dict[str, Any]:
    event = {
        "workflow_run_id": workflow_run_id,
        "action": action,
        "created_at": _now_iso(),
        "status": record.get("status"),
        "repair_kind": record.get("repair_kind"),
        "failure_category": record.get("failure_category"),
        "approved_by": record.get("approved_by"),
        "rejected_by": record.get("rejected_by"),
        "approval_note": record.get("approval_note"),
        "rejection_reason": record.get("rejection_reason"),
    }
    _REPAIR_APPROVAL_HISTORY.setdefault(workflow_run_id, []).append(event)
    return event


def _record_from_plan(
    *,
    workflow_run_id: str,
    repair_plan_result: Dict[str, Any],
    status: str,
    approved_by: Optional[str] = None,
    approval_note: Optional[str] = None,
    rejected_by: Optional[str] = None,
    rejection_reason: Optional[str] = None,
) -> Dict[str, Any]:
    repair_plan = repair_plan_result.get("repair_plan") or {}
    return {
        "workflow_run_id": workflow_run_id,
        "status": status,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "approved_by": approved_by,
        "approval_note": approval_note,
        "rejected_by": rejected_by,
        "rejection_reason": rejection_reason,
        "repair_kind": repair_plan.get("repair_kind"),
        "failure_category": repair_plan.get("failure_category"),
        "target_file_candidates": repair_plan.get("target_file_candidates") or [],
        "proposed_change_summary": repair_plan.get("proposed_change_summary"),
        "plan_needed": bool(repair_plan.get("plan_needed")),
        "source_repair_plan_status": repair_plan_result.get("repair_plan_status"),
        "source_safety_mode": repair_plan_result.get("safety_mode"),
    }


def get_repair_approval_status(workflow_run_id: str) -> Dict[str, Any]:
    record = _REPAIR_APPROVAL_RECORDS.get(workflow_run_id)
    approved = bool(record and record.get("status") == "approved")
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": REPAIR_APPROVAL_GATE_SAFETY_MODE,
        "approval_status": record.get("status") if record else "not_requested",
        "approved": approved,
        "blocked": not approved,
        "record": record,
        "history": _REPAIR_APPROVAL_HISTORY.get(workflow_run_id, []),
        "safety_flags": _safe_flags(approved=approved, blocked=not approved),
    }


def approve_repair_plan(
    *,
    workflow_run_id: str,
    approved_by: str = "platform_admin",
    approval_note: Optional[str] = None,
) -> Dict[str, Any]:
    repair_plan_result = generate_repair_plan_for_workflow(workflow_run_id)
    repair_plan = repair_plan_result.get("repair_plan") or {}
    if not repair_plan.get("plan_needed"):
        record = _record_from_plan(
            workflow_run_id=workflow_run_id,
            repair_plan_result=repair_plan_result,
            status="not_needed",
            approved_by=approved_by,
            approval_note=approval_note,
        )
        _REPAIR_APPROVAL_RECORDS[workflow_run_id] = record
        _history_event(workflow_run_id, "approval_not_needed", record)
        return get_repair_approval_status(workflow_run_id)

    record = _record_from_plan(
        workflow_run_id=workflow_run_id,
        repair_plan_result=repair_plan_result,
        status="approved",
        approved_by=approved_by,
        approval_note=approval_note,
    )
    _REPAIR_APPROVAL_RECORDS[workflow_run_id] = record
    _history_event(workflow_run_id, "approved", record)
    return get_repair_approval_status(workflow_run_id)


def reject_repair_plan(
    *,
    workflow_run_id: str,
    rejected_by: str = "platform_admin",
    rejection_reason: Optional[str] = None,
) -> Dict[str, Any]:
    repair_plan_result = generate_repair_plan_for_workflow(workflow_run_id)
    record = _record_from_plan(
        workflow_run_id=workflow_run_id,
        repair_plan_result=repair_plan_result,
        status="rejected",
        rejected_by=rejected_by,
        rejection_reason=rejection_reason,
    )
    _REPAIR_APPROVAL_RECORDS[workflow_run_id] = record
    _history_event(workflow_run_id, "rejected", record)
    return get_repair_approval_status(workflow_run_id)


def assert_repair_apply_allowed(workflow_run_id: str) -> Dict[str, Any]:
    status = get_repair_approval_status(workflow_run_id)
    allowed = bool(status.get("approved"))
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": REPAIR_APPROVAL_GATE_SAFETY_MODE,
        "apply_allowed": allowed,
        "blocked": not allowed,
        "block_reason": None if allowed else "Repair application is blocked until the repair plan is explicitly approved.",
        "approval_status": status.get("approval_status"),
        "record": status.get("record"),
        "safety_flags": _safe_flags(approved=allowed, blocked=not allowed),
    }


def reset_repair_approval_records_for_check() -> None:
    _REPAIR_APPROVAL_RECORDS.clear()
    _REPAIR_APPROVAL_HISTORY.clear()
