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
    request_kind: str = "platform_self_build",
    previous_scoping_request_id: Optional[str] = None,
) -> Dict[str, Any]:
    normalized = result.get("normalized_request") or {}
    version = 1
    if previous_scoping_request_id:
        previous = get_scoping_record(db, previous_scoping_request_id)
        if previous is not None:
            version = previous.version + 1

    record = PlatformScopingRequest(
        scoping_request_id=f"scope-{uuid4()}",
        status=str(result.get("status") or "unknown"),
        approval_status="approval_required" if result.get("approval_required") else "not_approved",
        requested_by=requested_by,
        request_kind=request_kind,
        version=version,
        previous_scoping_request_id=previous_scoping_request_id,
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


def link_scoping_record_to_workflow_run(
    db: Session,
    *,
    scoping_request_id: str,
    workflow_run_id: str,
) -> Optional[Dict[str, Any]]:
    record = get_scoping_record(db, scoping_request_id)
    if record is None:
        return None
    record.workflow_run_id = workflow_run_id
    record.updated_at = utc_now()
    db.commit()
    db.refresh(record)
    return serialize_scoping_record(record)


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
