# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
from typing import Any, Dict, List, Optional
from app.platform.services.persistent_state_store_service import (
    add_self_build_module_request_event,
    get_self_build_module_request_record,
    list_self_build_module_request_events,
    list_self_build_module_request_records,
    next_self_build_module_request_id,
    record_self_build_module_request,
    reset_v82_persistent_state_for_check,
    update_self_build_module_request,
)
from app.platform.services.self_healing_loop_coordinator_service import inspect_self_healing_loop
SELF_BUILD_MODULE_REQUEST_SAFETY_MODE = "self_build_module_request_v78_request_tracking_only"

def _safe_flags(*, handoff_checked: bool = False) -> Dict[str, bool]:
    return {
        "self_build_module_request_checked": True,
        "request_tracking_only": True,
        "handoff_checked": handoff_checked,
        "persistent_state_store_used": True,
        "workflow_created_by_request_service": False,
        "generated_files_written": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "generated_code_execution_performed": False,
        "runtime_server_started": False,
        "install_packages_performed": False,
        "auto_approval_performed": False,
        "approval_bypass_performed": False,
        "repair_applied": False,
        "unapproved_repair_applied": False,
        "restore_executed": False,
        "module_rollout_performed": False,
    }

def _normalize_text(value: Any, *, max_length: int = 2000) -> str:
    text = str(value or "").strip()
    return text[:max_length]

def _normalize_module_name(value: Any) -> str:
    text = _normalize_text(value, max_length=120)
    if not text:
        return "Untitled Module"
    return " ".join(text.split())

def _history_event(request_id: str, action: str, record: Dict[str, Any], details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return add_self_build_module_request_event(
        request_id=request_id,
        action=action,
        status=record.get("status"),
        workflow_run_id=record.get("workflow_run_id"),
        module_name=record.get("module_name"),
        details=details or {},
    )

def create_self_build_module_request(
    *,
    module_name: Any,
    module_goal: Any,
    requested_by: str = "platform_admin",
    workflow_run_id: Optional[str] = None,
    acceptance_criteria: Optional[List[Any]] = None,
    notes: Any = None,
    initial_status: str = "request_recorded",
) -> Dict[str, Any]:
    request_id = next_self_build_module_request_id()
    normalized_criteria = [
        _normalize_text(item, max_length=300)
        for item in (acceptance_criteria or [])
        if _normalize_text(item, max_length=300)
    ]
    record = record_self_build_module_request(
        {
            "request_id": request_id,
            "status": _normalize_text(initial_status, max_length=80) or "request_recorded",
            "requested_by": _normalize_text(requested_by, max_length=120) or "platform_admin",
            "module_name": _normalize_module_name(module_name),
            "module_goal": _normalize_text(module_goal),
            "acceptance_criteria": normalized_criteria,
            "notes": _normalize_text(notes, max_length=1000),
            "workflow_run_id": _normalize_text(workflow_run_id, max_length=120) or None,
            "handoff_status": "linked_to_existing_workflow" if workflow_run_id else "waiting_for_app_build_workflow",
        }
    )
    _history_event(request_id, "created", record)
    return {
        "success": True,
        "safety_mode": SELF_BUILD_MODULE_REQUEST_SAFETY_MODE,
        "request": record,
        "history": list_self_build_module_request_events(request_id),
        "safety_flags": _safe_flags(handoff_checked=False),
    }

def link_self_build_module_request_to_workflow(
    *,
    request_id: str,
    workflow_run_id: str,
    linked_by: str = "platform_admin",
) -> Dict[str, Any]:
    record = get_self_build_module_request_record(request_id)
    if not record:
        return {
            "success": True,
            "safety_mode": SELF_BUILD_MODULE_REQUEST_SAFETY_MODE,
            "request_id": request_id,
            "status": "not_found",
            "request": None,
            "history": [],
            "safety_flags": _safe_flags(handoff_checked=False),
        }
    workflow_run_id = _normalize_text(workflow_run_id, max_length=120) or None
    linked_by = _normalize_text(linked_by, max_length=120) or "platform_admin"
    record = update_self_build_module_request(
        request_id,
        {
            "workflow_run_id": workflow_run_id,
            "linked_by": linked_by,
            "status": "linked_to_workflow" if workflow_run_id else "request_recorded",
            "handoff_status": "linked_to_existing_workflow" if workflow_run_id else "waiting_for_app_build_workflow",
        },
    )
    _history_event(request_id, "linked_to_workflow", record, {"linked_by": linked_by})
    return {
        "success": True,
        "safety_mode": SELF_BUILD_MODULE_REQUEST_SAFETY_MODE,
        "request": record,
        "history": list_self_build_module_request_events(request_id),
        "safety_flags": _safe_flags(handoff_checked=False),
    }

def get_self_build_module_request(request_id: str) -> Dict[str, Any]:
    record = get_self_build_module_request_record(request_id)
    return {
        "success": True,
        "safety_mode": SELF_BUILD_MODULE_REQUEST_SAFETY_MODE,
        "request_id": request_id,
        "status": record.get("status") if record else "not_found",
        "request": record,
        "history": list_self_build_module_request_events(request_id) if record else [],
        "safety_flags": _safe_flags(handoff_checked=False),
    }
