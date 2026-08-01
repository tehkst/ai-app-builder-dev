from __future__ import annotations

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
    attachments: Optional[List[Dict[str, Any]]] = None,
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
        attachments_json=_json(attachments or []),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return serialize_scoping_record(record)


def request_publish_for_scoping_record(
    db: Session,
    *,
    scoping_request_id: str,
    requested_by: str,
) -> Dict[str, Any]:
    """Record a customer's request to publish a completed build.

    This does not deploy anything itself - it only marks the request so a founder
    can review and run the existing founder-approved Cloud Run deploy flow
    (app.platform.deployment.approved_cloud_run), the same governance gate every
    other live deploy on this platform goes through. There is no automated,
    unreviewed path from "customer clicks Publish" to "live on the public
    internet" - AI-generated code getting a founder look before it's publicly
    reachable is a deliberate, existing platform-wide safety boundary, not an
    oversight to route around here.
    """

    record = get_scoping_record(db, scoping_request_id)
    if record is None:
        return {"success": False, "status": "scoping_request_not_found"}
    if record.requested_by != requested_by:
        return {"success": False, "status": "forbidden"}
    if not record.workflow_run_id:
        return {"success": False, "status": "no_build_to_publish"}
    if record.publish_status == "requested":
        return {"success": True, "status": "already_requested", **serialize_scoping_record(record)}
    if record.publish_status in {"approved", "pr_created", "live"}:
        # A founder decision (or a completed launch) is already in motion; resetting it
        # back to "requested" here would silently discard that progress. A customer can
        # only ask again after an explicit rejection, not skip ahead of an in-flight or
        # completed publish.
        return {"success": False, "status": "publish_already_in_progress", **serialize_scoping_record(record)}

    record.publish_status = "requested"
    record.publish_requested_at = utc_now()
    record.updated_at = utc_now()
    db.commit()
    db.refresh(record)
    return {"success": True, "status": "requested", **serialize_scoping_record(record)}


def list_requested_publishes(db: Session) -> List[Dict[str, Any]]:
    """Every build a customer has asked to publish, still awaiting a founder decision.

    'requested' means the customer clicked Request publish and no founder action has
    happened yet; 'approved' means a founder approved it but materialization (turning
    the build into a real reviewable PR - see publish_review service) hasn't completed
    yet, so it still needs to show up here rather than disappearing from view.
    """
    records = (
        db.query(PlatformScopingRequest)
        .filter(PlatformScopingRequest.publish_status.in_(["requested", "approved"]))
        .order_by(PlatformScopingRequest.publish_requested_at.desc())
        .all()
    )
    return [serialize_scoping_record(record) for record in records]


def approve_publish_for_scoping_record(
    db: Session,
    *,
    scoping_request_id: str,
    approved_by: str,
) -> Optional[Dict[str, Any]]:
    record = get_scoping_record(db, scoping_request_id)
    if record is None or record.publish_status != "requested":
        return None
    record.publish_status = "approved"
    record.approved_by = approved_by
    record.updated_at = utc_now()
    db.commit()
    db.refresh(record)
    return serialize_scoping_record(record)


def reject_publish_for_scoping_record(
    db: Session,
    *,
    scoping_request_id: str,
    rejected_by: str,
) -> Optional[Dict[str, Any]]:
    record = get_scoping_record(db, scoping_request_id)
    if record is None or record.publish_status not in {"requested", "approved"}:
        return None
    record.publish_status = "rejected"
    record.publish_rejected_at = utc_now()
    record.approved_by = rejected_by
    record.updated_at = utc_now()
    db.commit()
    db.refresh(record)
    return serialize_scoping_record(record)


def mark_publish_pull_request_created(
    db: Session,
    *,
    scoping_request_id: str,
    app_id: str,
    pull_request_url: str,
    pull_request_number: int,
) -> Optional[Dict[str, Any]]:
    record = get_scoping_record(db, scoping_request_id)
    if record is None:
        return None
    record.publish_status = "pr_created"
    record.publish_app_id = app_id
    record.publish_pull_request_url = pull_request_url
    record.publish_pull_request_number = pull_request_number
    record.updated_at = utc_now()
    db.commit()
    db.refresh(record)
    return serialize_scoping_record(record)


def mark_scoping_record_live(
    db: Session,
    *,
    scoping_request_id: str,
    live_url: str,
) -> Optional[Dict[str, Any]]:
    record = get_scoping_record(db, scoping_request_id)
    if record is None:
        return None
    record.publish_status = "live"
    record.live_url = live_url
    record.published_at = utc_now()
    record.updated_at = utc_now()
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
