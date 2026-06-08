from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.platform.services.persistent_state_store_service import (
    add_module_rollout_event,
    get_module_rollout_decision,
    list_module_rollout_events,
    reset_v82_persistent_state_for_check,
    upsert_module_rollout_decision,
)
from app.platform.services.self_build_module_request_service import (
    get_self_build_module_request,
    inspect_self_build_module_request_handoff,
)


MODULE_ROLLOUT_GATE_SAFETY_MODE = "module_rollout_gate_v79_gate_only"

_ELIGIBLE_LOOP_STATUSES = {"healthy_no_repair_needed", "self_healing_loop_completed"}


def _safe_flags(*, handoff_checked: bool = False, approval_recorded: bool = False) -> Dict[str, bool]:
    return {
        "module_rollout_gate_checked": True,
        "rollout_gate_only": True,
        "rollout_eligibility_checked": True,
        "handoff_checked": handoff_checked,
        "rollout_approval_recorded": approval_recorded,
        "persistent_state_store_used": True,
        "rollout_execution_performed": False,
        "module_rollout_performed": False,
        "production_file_write_performed": False,
        "live_module_modified": False,
        "auto_approval_performed": False,
        "approval_bypass_performed": False,
        "generated_code_execution_performed": False,
        "runtime_server_started": False,
        "install_packages_performed": False,
        "repair_applied": False,
        "unapproved_repair_applied": False,
        "restore_executed": False,
    }


def _history_event(request_id: str, action: str, status: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return add_module_rollout_event(
        request_id=request_id,
        action=action,
        status=status,
        details=details or {},
    )


def inspect_module_rollout_gate(request_id: str) -> Dict[str, Any]:
    request_result = get_self_build_module_request(request_id)
    request_record = request_result.get("request")
    handoff_result = None
    loop_status = None
    workflow_run_id = None
    eligibility_reasons: List[str] = []

    if not request_record:
        eligibility_status = "not_found"
        eligible = False
        eligibility_reasons.append("Module request was not found.")
    else:
        workflow_run_id = request_record.get("workflow_run_id")
        if not workflow_run_id:
            eligibility_status = "not_eligible"
            eligible = False
            eligibility_reasons.append("Module request is not linked to a workflow_run_id.")
        else:
            handoff_result = inspect_self_build_module_request_handoff(request_id)
            loop_status = ((handoff_result.get("self_healing_loop") or {}).get("loop_status"))
            if loop_status in _ELIGIBLE_LOOP_STATUSES:
                eligibility_status = "eligible_for_rollout_approval"
                eligible = True
                eligibility_reasons.append("Linked workflow has an eligible V77 self-healing loop status.")
            else:
                eligibility_status = "not_eligible"
                eligible = False
                eligibility_reasons.append("Linked workflow is not yet healthy or completed through the V77 loop.")

    approval_record = get_module_rollout_decision(request_id)
    rollout_status = "waiting_for_eligibility"
    if eligible:
        rollout_status = "waiting_for_rollout_approval"
    if approval_record:
        rollout_status = approval_record.get("approval_status", rollout_status)

    return {
        "success": True,
        "safety_mode": MODULE_ROLLOUT_GATE_SAFETY_MODE,
        "request_id": request_id,
        "workflow_run_id": workflow_run_id,
        "eligible": eligible,
        "eligibility_status": eligibility_status,
        "eligibility_reasons": eligibility_reasons,
        "rollout_status": rollout_status,
        "approval_record": approval_record,
        "request_result": request_result,
        "handoff_result": handoff_result,
        "loop_status": loop_status,
        "history": list_module_rollout_events(request_id),
        "safety_flags": _safe_flags(handoff_checked=handoff_result is not None, approval_recorded=approval_record is not None),
    }


def approve_module_rollout(
    *,
    request_id: str,
    approved_by: str = "platform_admin",
    reason: Any = None,
) -> Dict[str, Any]:
    gate = inspect_module_rollout_gate(request_id)
    if not gate.get("eligible"):
        _history_event(
            request_id,
            "approval_blocked_not_eligible",
            "blocked",
            {"reason": str(reason or ""), "eligibility_status": gate.get("eligibility_status")},
        )
        gate["rollout_status"] = "approval_blocked_not_eligible"
        gate["approval_record"] = None
        gate["history"] = list_module_rollout_events(request_id)
        gate["safety_flags"] = _safe_flags(handoff_checked=gate.get("handoff_result") is not None, approval_recorded=False)
        return gate

    record = upsert_module_rollout_decision(
        {
            "request_id": request_id,
            "approval_status": "rollout_approved",
            "approved": True,
            "rejected": False,
            "approved_by": str(approved_by or "platform_admin"),
            "reason": str(reason or ""),
            "rollout_execution_allowed": False,
            "rollout_execution_performed": False,
        }
    )
    _history_event(request_id, "rollout_approved", "rollout_approved", {"approved_by": record["approved_by"]})
    gate = inspect_module_rollout_gate(request_id)
    gate["approval_record"] = record
    gate["rollout_status"] = "rollout_approved"
    gate["history"] = list_module_rollout_events(request_id)
    gate["safety_flags"] = _safe_flags(handoff_checked=gate.get("handoff_result") is not None, approval_recorded=True)
    return gate


def reject_module_rollout(
    *,
    request_id: str,
    rejected_by: str = "platform_admin",
    reason: Any = None,
) -> Dict[str, Any]:
    record = upsert_module_rollout_decision(
        {
            "request_id": request_id,
            "approval_status": "rollout_rejected",
            "approved": False,
            "rejected": True,
            "rejected_by": str(rejected_by or "platform_admin"),
            "reason": str(reason or ""),
            "rollout_execution_allowed": False,
            "rollout_execution_performed": False,
        }
    )
    _history_event(request_id, "rollout_rejected", "rollout_rejected", {"rejected_by": record["rejected_by"]})
    gate = inspect_module_rollout_gate(request_id)
    gate["approval_record"] = record
    gate["rollout_status"] = "rollout_rejected"
    gate["history"] = list_module_rollout_events(request_id)
    gate["safety_flags"] = _safe_flags(handoff_checked=gate.get("handoff_result") is not None, approval_recorded=True)
    return gate


def get_module_rollout_history(request_id: str) -> Dict[str, Any]:
    return {
        "success": True,
        "safety_mode": MODULE_ROLLOUT_GATE_SAFETY_MODE,
        "request_id": request_id,
        "approval_record": get_module_rollout_decision(request_id),
        "history": list_module_rollout_events(request_id),
        "safety_flags": _safe_flags(handoff_checked=False, approval_recorded=get_module_rollout_decision(request_id) is not None),
    }


def reset_module_rollout_gate_for_check() -> None:
    reset_v82_persistent_state_for_check()
