from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.persistence.model_definitions.base import utc_now
from app.platform.persistence.models import PlatformScopingRequest


def list_scoping_version_chain(db: Session, scoping_request_id: str) -> List[Dict[str, Any]]:
    """Return every version linked to the given SOW, oldest first."""

    record = get_scoping_record(db, scoping_request_id)
    if record is None:
        return []

    root_id = record.scoping_request_id
    seen_ids = {root_id}
    cursor = record
    while cursor.previous_scoping_request_id:
        parent = get_scoping_record(db, cursor.previous_scoping_request_id)
        if parent is None or parent.scoping_request_id in seen_ids:
            break
        root_id = parent.scoping_request_id
        seen_ids.add(root_id)
        cursor = parent

    chain: List[Dict[str, Any]] = []
    current_id = root_id
    guard = 0
    while current_id and guard < 200:
        guard += 1
        current = get_scoping_record(db, current_id)
        if current is None:
            break
        chain.append(serialize_scoping_record(current))
        next_record = (
            db.query(PlatformScopingRequest)
            .filter(PlatformScopingRequest.previous_scoping_request_id == current_id)
            .order_by(PlatformScopingRequest.id.asc())
            .first()
        )
        current_id = next_record.scoping_request_id if next_record else None

    return chain


def delete_scoping_chain(db: Session, *, scoping_request_id: str, requested_by: str) -> bool:
    """Delete every version in this SOW's chain, not just the given id.

    Each amendment persists a new row rather than mutating the original (see
    amend_scope), so deleting only the leaf would leave orphaned earlier
    versions behind and the project would still resurface via those rows.
    """

    chain = list_scoping_version_chain(db, scoping_request_id)
    if not chain or any(item["requested_by"] != requested_by for item in chain):
        return False
    for item in chain:
        record = get_scoping_record(db, item["scoping_request_id"])
        if record is not None:
            db.delete(record)
    db.commit()
    return True


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


def list_scoping_records_for_user(db: Session, requested_by: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Return the latest version of each SOW chain owned by this user, most recently updated first.

    Each amendment (see amend_scope) persists a new row linked via previous_scoping_request_id
    rather than mutating the original, so a single logical project can span several rows -
    this collapses each chain down to its newest version before returning.
    """

    records = (
        db.query(PlatformScopingRequest)
        .filter(PlatformScopingRequest.requested_by == requested_by)
        .all()
    )
    by_id = {record.scoping_request_id: record for record in records}

    def _root_id(record: PlatformScopingRequest) -> str:
        seen = {record.scoping_request_id}
        cursor = record
        while cursor.previous_scoping_request_id and cursor.previous_scoping_request_id in by_id:
            parent = by_id[cursor.previous_scoping_request_id]
            if parent.scoping_request_id in seen:
                break
            cursor = parent
            seen.add(cursor.scoping_request_id)
        return cursor.scoping_request_id

    latest_by_root: Dict[str, PlatformScopingRequest] = {}
    for record in records:
        root_id = _root_id(record)
        existing = latest_by_root.get(root_id)
        if existing is None or record.version > existing.version:
            latest_by_root[root_id] = record

    ordered = sorted(latest_by_root.values(), key=lambda record: record.updated_at, reverse=True)
    return [serialize_scoping_record(record) for record in ordered[:limit]]


def serialize_scoping_record(record: PlatformScopingRequest) -> Dict[str, Any]:
    return {
        "scoping_request_id": record.scoping_request_id,
        "status": record.status,
        "approval_status": record.approval_status,
        "requested_by": record.requested_by,
        "request_kind": record.request_kind,
        "version": record.version,
        "previous_scoping_request_id": record.previous_scoping_request_id,
        "workflow_run_id": record.workflow_run_id,
        "normalized_request": _loads(record.normalized_request_json, {}),
        "questions": _loads(record.questions_json, []),
        "scope_of_work_markdown": record.scope_of_work_markdown,
        "milestone_tree": _loads(record.milestone_tree_json, []),
        "safety_flags": _loads(record.safety_flags_json, {}),
        "llm_status": record.llm_status,
        "llm_notes": _loads(record.llm_notes_json, {}),
        "attachments": _loads(record.attachments_json, []),
        "publish_status": record.publish_status,
        "publish_requested_at": record.publish_requested_at.isoformat() if record.publish_requested_at else None,
        "publish_rejected_at": record.publish_rejected_at.isoformat() if record.publish_rejected_at else None,
        "publish_app_id": record.publish_app_id,
        "publish_pull_request_url": record.publish_pull_request_url,
        "publish_pull_request_number": record.publish_pull_request_number,
        "live_url": record.live_url,
        "published_at": record.published_at.isoformat() if record.published_at else None,
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
