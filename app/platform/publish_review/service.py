from __future__ import annotations

from typing import Any, Dict, Optional

from app.platform.auth.service import require_founder
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.scoping_persistence_service import (
    approve_publish_for_scoping_record,
    list_requested_publishes,
    reject_publish_for_scoping_record,
)
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail

CONTRACT = "publish-review-v1"


def _unauthorised() -> Dict[str, Any]:
    return {"contract": CONTRACT, "status": "unauthorized", "authenticated": False}


def _build_summary(db, workflow_run_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not workflow_run_id:
        return None
    detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
    if not detail.get("found"):
        return None
    return {
        "status": detail.get("status"),
        "step_count": detail.get("step_count"),
        "completed_step_count": detail.get("completed_step_count"),
        "failed_step_count": detail.get("failed_step_count"),
        "completed_at": detail.get("completed_at"),
    }


def list_pending_publish_requests(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return _unauthorised()
    create_platform_tables()
    items = []
    with PlatformSessionLocal() as db:
        for record in list_requested_publishes(db):
            build = _build_summary(db, record.get("workflow_run_id"))
            items.append({
                "scoping_request_id": record["scoping_request_id"],
                "project_name": (record.get("normalized_request") or {}).get("app_idea") or "Untitled project",
                "owner": record.get("requested_by"),
                "scope_of_work_markdown": record.get("scope_of_work_markdown"),
                "publish_status": record.get("publish_status"),
                "publish_requested_at": record.get("publish_requested_at"),
                "workflow_run_id": record.get("workflow_run_id"),
                "publish_app_id": record.get("publish_app_id"),
                "publish_pull_request_url": record.get("publish_pull_request_url"),
                "build": build,
                "build_completed": bool(build and build.get("status") == "completed"),
            })
    return {"contract": CONTRACT, "status": "ready", "requests": items}


def approve_publish_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return _unauthorised()
    scoping_request_id = str(payload.get("scoping_request_id") or "").strip()
    if not scoping_request_id:
        return {"contract": CONTRACT, "status": "invalid-request", "error": "scoping_request_id is required."}
    create_platform_tables()
    with PlatformSessionLocal() as db:
        record = approve_publish_for_scoping_record(
            db, scoping_request_id=scoping_request_id, approved_by=str(founder.get("email") or "founder"),
        )
    if record is None:
        return {
            "contract": CONTRACT, "status": "not_found_or_invalid_state", "scoping_request_id": scoping_request_id,
            "error": "This request was not found, or is no longer awaiting a founder decision.",
        }
    return {"contract": CONTRACT, "status": "approved", "request": record}


def reject_publish_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return _unauthorised()
    scoping_request_id = str(payload.get("scoping_request_id") or "").strip()
    if not scoping_request_id:
        return {"contract": CONTRACT, "status": "invalid-request", "error": "scoping_request_id is required."}
    create_platform_tables()
    with PlatformSessionLocal() as db:
        record = reject_publish_for_scoping_record(
            db, scoping_request_id=scoping_request_id, rejected_by=str(founder.get("email") or "founder"),
        )
    if record is None:
        return {
            "contract": CONTRACT, "status": "not_found_or_invalid_state", "scoping_request_id": scoping_request_id,
            "error": "This request was not found, or is no longer awaiting a founder decision.",
        }
    return {"contract": CONTRACT, "status": "rejected", "request": record}
