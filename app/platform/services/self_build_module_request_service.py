from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.platform.services.self_healing_loop_coordinator_service import inspect_self_healing_loop


SELF_BUILD_MODULE_REQUEST_SAFETY_MODE = "self_build_module_request_v78_request_tracking_only"
_SELF_BUILD_MODULE_REQUESTS: Dict[str, Dict[str, Any]] = {}
_SELF_BUILD_MODULE_REQUEST_HISTORY: Dict[str, List[Dict[str, Any]]] = {}
_COUNTER = 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_flags(*, handoff_checked: bool = False) -> Dict[str, bool]:
    return {
        "self_build_module_request_checked": True,
        "request_tracking_only": True,
        "handoff_checked": handoff_checked,
        "workflow_created_by_request_service": False,
        "generated_files_written": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "generated_code_execution_performed": False,
        "runtime_server_started": False,
        "install_packages_performed": False,
        "auto_approval_performed": False,
        "repair_applied": False,
        "unapproved_repair_applied": False,
        "restore_executed": False,
        "module_rollout_performed": False,
    }


def _next_request_id() -> str:
    global _COUNTER
    _COUNTER += 1
    return f"module-request-{_COUNTER:04d}"


def _normalize_text(value: Any, *, max_length: int = 2000) -> str:
    text = str(value or "").strip()
    return text[:max_length]


def _normalize_module_name(value: Any) -> str:
    text = _normalize_text(value, max_length=120)
    if not text:
        return "Untitled Module"
    return " ".join(text.split())


def _history_event(request_id: str, action: str, record: Dict[str, Any], details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    event = {
        "request_id": request_id,
        "action": action,
        "status": record.get("status"),
        "created_at": _now_iso(),
        "workflow_run_id": record.get("workflow_run_id"),
        "module_name": record.get("module_name"),
        "details": details or {},
    }
    _SELF_BUILD_MODULE_REQUEST_HISTORY.setdefault(request_id, []).append(event)
    return event


def create_self_build_module_request(
    *,
    module_name: Any,
    module_goal: Any,
    requested_by: str = "platform_admin",
    workflow_run_id: Optional[str] = None,
    acceptance_criteria: Optional[List[Any]] = None,
    notes: Any = None,
) -> Dict[str, Any]:
    request_id = _next_request_id()
    normalized_criteria = [
        _normalize_text(item, max_length=300)
        for item in (acceptance_criteria or [])
        if _normalize_text(item, max_length=300)
    ]
    record = {
        "request_id": request_id,
        "status": "request_recorded",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "requested_by": _normalize_text(requested_by, max_length=120) or "platform_admin",
        "module_name": _normalize_module_name(module_name),
        "module_goal": _normalize_text(module_goal),
        "acceptance_criteria": normalized_criteria,
        "notes": _normalize_text(notes, max_length=1000),
        "workflow_run_id": _normalize_text(workflow_run_id, max_length=120) or None,
        "handoff_status": "linked_to_existing_workflow" if workflow_run_id else "waiting_for_app_build_workflow",
    }
    _SELF_BUILD_MODULE_REQUESTS[request_id] = record
    _history_event(request_id, "created", record)
    return {
        "success": True,
        "safety_mode": SELF_BUILD_MODULE_REQUEST_SAFETY_MODE,
        "request": record,
        "history": _SELF_BUILD_MODULE_REQUEST_HISTORY.get(request_id, []),
        "safety_flags": _safe_flags(handoff_checked=False),
    }


def link_self_build_module_request_to_workflow(
    *,
    request_id: str,
    workflow_run_id: str,
    linked_by: str = "platform_admin",
) -> Dict[str, Any]:
    record = _SELF_BUILD_MODULE_REQUESTS.get(request_id)
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
    record["workflow_run_id"] = _normalize_text(workflow_run_id, max_length=120) or None
    record["updated_at"] = _now_iso()
    record["linked_by"] = _normalize_text(linked_by, max_length=120) or "platform_admin"
    record["status"] = "linked_to_workflow" if record["workflow_run_id"] else "request_recorded"
    record["handoff_status"] = "linked_to_existing_workflow" if record["workflow_run_id"] else "waiting_for_app_build_workflow"
    _history_event(request_id, "linked_to_workflow", record, {"linked_by": record["linked_by"]})
    return {
        "success": True,
        "safety_mode": SELF_BUILD_MODULE_REQUEST_SAFETY_MODE,
        "request": record,
        "history": _SELF_BUILD_MODULE_REQUEST_HISTORY.get(request_id, []),
        "safety_flags": _safe_flags(handoff_checked=False),
    }


def get_self_build_module_request(request_id: str) -> Dict[str, Any]:
    record = _SELF_BUILD_MODULE_REQUESTS.get(request_id)
    return {
        "success": True,
        "safety_mode": SELF_BUILD_MODULE_REQUEST_SAFETY_MODE,
        "request_id": request_id,
        "status": record.get("status") if record else "not_found",
        "request": record,
        "history": _SELF_BUILD_MODULE_REQUEST_HISTORY.get(request_id, []),
        "safety_flags": _safe_flags(handoff_checked=False),
    }


def list_self_build_module_requests() -> Dict[str, Any]:
    requests = sorted(
        _SELF_BUILD_MODULE_REQUESTS.values(),
        key=lambda record: record.get("created_at") or "",
        reverse=True,
    )
    return {
        "success": True,
        "safety_mode": SELF_BUILD_MODULE_REQUEST_SAFETY_MODE,
        "requests": requests,
        "count": len(requests),
        "safety_flags": _safe_flags(handoff_checked=False),
    }


def inspect_self_build_module_request_handoff(request_id: str) -> Dict[str, Any]:
    record = _SELF_BUILD_MODULE_REQUESTS.get(request_id)
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
        record["handoff_status"] = loop_status.get("loop_status") or "linked_to_existing_workflow"
        record["updated_at"] = _now_iso()
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
        "history": _SELF_BUILD_MODULE_REQUEST_HISTORY.get(request_id, []),
        "safety_flags": _safe_flags(handoff_checked=bool(workflow_run_id)),
    }


def reset_self_build_module_requests_for_check() -> None:
    global _COUNTER
    _SELF_BUILD_MODULE_REQUESTS.clear()
    _SELF_BUILD_MODULE_REQUEST_HISTORY.clear()
    _COUNTER = 0
