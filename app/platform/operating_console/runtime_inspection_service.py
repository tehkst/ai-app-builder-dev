from __future__ import annotations

from typing import Any

from app.platform.auth.service import require_founder
from app.platform.persistence.database import PlatformSessionLocal
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail

SUPPORTED_INSPECTION_TYPE = "workflow_run"


def inspect_runtime(payload: dict[str, Any]) -> dict[str, Any]:
    authorization = require_founder(payload)
    if not authorization.get("authorized"):
        return {
            "status": "blocked",
            "authorized": False,
            "reason": "founder_authorization_required",
        }

    inspection_type = str(payload.get("type") or "").strip()
    workflow_run_id = str(payload.get("id") or payload.get("workflow_run_id") or "").strip()

    if inspection_type != SUPPORTED_INSPECTION_TYPE:
        return {
            "status": "invalid_request",
            "authorized": True,
            "reason": "unsupported_inspection_type",
            "supported_types": [SUPPORTED_INSPECTION_TYPE],
        }
    if not workflow_run_id:
        return {
            "status": "invalid_request",
            "authorized": True,
            "reason": "workflow_run_id_required",
        }

    db = PlatformSessionLocal()
    try:
        detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
    finally:
        db.close()

    if not detail.get("found"):
        return {
            "status": "not_found",
            "authorized": True,
            "found": False,
            "workflow_run_id": workflow_run_id,
            "steps": [],
        }

    return {
        "status": "inspection_complete",
        "authorized": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "workflow_name": detail.get("workflow_name"),
        "workflow_status": detail.get("status"),
        "step_count": detail.get("step_count"),
        "steps": [_summarize_step(step) for step in detail.get("steps") or []],
    }


def _summarize_step(step: dict[str, Any]) -> dict[str, Any]:
    handler_result = step.get("handler_result")
    if not isinstance(handler_result, dict):
        handler_result = {}
    change_set = handler_result.get("change_set")
    has_change_set = isinstance(change_set, dict)

    return {
        "step_id": step.get("step_id"),
        "step_run_id": step.get("step_run_id"),
        "status": step.get("status"),
        "handler_keys": sorted(str(key) for key in handler_result.keys()),
        "has_change_set": has_change_set,
        "change_set_keys": sorted(str(key) for key in change_set.keys()) if has_change_set else [],
        "error_keys": _dictionary_keys(step.get("error")),
    }


def _dictionary_keys(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    return sorted(str(key) for key in value.keys())
