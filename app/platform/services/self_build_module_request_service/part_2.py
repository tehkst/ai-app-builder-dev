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

def list_self_build_module_requests() -> Dict[str, Any]:
    requests = list_self_build_module_request_records()
    return {
        "success": True,
        "safety_mode": SELF_BUILD_MODULE_REQUEST_SAFETY_MODE,
        "requests": requests,
        "count": len(requests),
        "safety_flags": _safe_flags(handoff_checked=False),
    }

def inspect_self_build_module_request_handoff(request_id: str) -> Dict[str, Any]:
    record = get_self_build_module_request_record(request_id)
    if not record:
        return {
            "success": True,
            "safety_mode": SELF_BUILD_MODULE_REQUEST_SAFETY_MODE,
            "request_id": request_id,
            "status": "not_found",
            "request": None,
            "self_healing_loop": None,
            "safety_flags": _safe_flags(handoff_checked=False),
        }
    workflow_run_id = record.get("workflow_run_id")
    loop_status = None
    if workflow_run_id:
        loop_status = inspect_self_healing_loop(workflow_run_id=workflow_run_id)
        record = update_self_build_module_request(
            request_id,
            {"handoff_status": loop_status.get("loop_status") or "linked_to_existing_workflow"},
        )
        _history_event(
            request_id,
            "handoff_checked",
            record,
            {
                "workflow_run_id": workflow_run_id,
                "loop_status": loop_status.get("loop_status"),
                "next_required_action": loop_status.get("next_required_action"),
            },
        )
    return {
        "success": True,
        "safety_mode": SELF_BUILD_MODULE_REQUEST_SAFETY_MODE,
        "request_id": request_id,
        "status": record.get("status"),
        "request": record,
        "self_healing_loop": loop_status,
        "history": list_self_build_module_request_events(request_id),
        "safety_flags": _safe_flags(handoff_checked=bool(workflow_run_id)),
    }

def reset_self_build_module_requests_for_check() -> None:
    reset_v82_persistent_state_for_check()
