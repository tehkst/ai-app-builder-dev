from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.platform.persistence.model_definitions.base import utc_now
from app.platform.persistence.models import PlatformScopingRequest


def persist_scoping_analysis(
    db: Session,
    *,
    result: Dict[str, Any],
    llm_result: Dict[str, Any],
    requested_by: str = "platform_admin",
) -> Dict[str, Any]:
    normalized = result.get("normalized_request") or {}
    record = PlatformScopingRequest(
        scoping_request_id=f"scope-{uuid4()}",
        status=str(result.get("status") or "unknown"),
        approval_status="approval_required" if result.get("approval_required") else "not_approved",
        requested_by=requested_by,
        mode_selector=normalized.get("mode_selector"),
        target_boundary=normalized.get("target_boundary"),
        change_classification=normalized.get("change_classification"),
        normalized_request_json=_json(normalized),
        questions_json=_json(result.get("questions") or []),
        scope_of_work_markdown=str(result.get("scope_of_work_markdown") or ""),
        milestone_tree_json=_json(result.get("milestone_tree") or []),
        safety_flags_json=_json(result.get("safety_flags") or {}),
        llm_status=str(llm_result.get("status") or "not_requested"),
        llm_notes_json=_json(llm_result.get("notes") or {}),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return serialize_scoping_record(record)


def approve_scoping_record(
    db: Session,
    *,
    scoping_request_id: str,
    approved_by: str = "platform_admin",
) -> Optional[Dict[str, Any]]:
    record = get_scoping_record(db, scoping_request_id)
    if record is None:
        return None
    record.approval_status = "scope_approved"
    record.status = "approved"
    record.approved_by = approved_by
    record.approved_at = utc_now()
    record.updated_at = utc_now()
    db.commit()
    db.refresh(record)
    return serialize_scoping_record(record)


def get_scoping_record(db: Session, scoping_request_id: str) -> Optional[PlatformScopingRequest]:
    return (
        db.query(PlatformScopingRequest)
        .filter(PlatformScopingRequest.scoping_request_id == scoping_request_id)
        .first()
    )


def list_recent_scoping_records(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    records = (
        db.query(PlatformScopingRequest)
        .order_by(PlatformScopingRequest.id.desc())
        .limit(limit)
        .all()
    )
    return [serialize_scoping_record(record) for record in records]


def serialize_scoping_record(record: PlatformScopingRequest) -> Dict[str, Any]:
    return {
        "scoping_request_id": record.scoping_request_id,
        "status": record.status,
        "approval_status": record.approval_status,
        "requested_by": record.requested_by,
        "normalized_request": _loads(record.normalized_request_json, {}),
        "questions": _loads(record.questions_json, []),
        "scope_of_work_markdown": record.scope_of_work_markdown,
        "milestone_tree": _loads(record.milestone_tree_json, []),
        "safety_flags": _loads(record.safety_flags_json, {}),
        "llm_status": record.llm_status,
        "llm_notes": _loads(record.llm_notes_json, {}),
        "approved_by": record.approved_by,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, sort_keys=True)


def _loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except json.JSONDecodeError:
        return fallback
