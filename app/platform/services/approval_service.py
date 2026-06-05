import json
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.platform.persistence.models import (
    PlatformApprovalRequest,
    PlatformAuditEvent,
    utc_now,
)

PENDING_APPROVAL_STATUS = "pending"


def approval_to_dict(approval: PlatformApprovalRequest) -> dict:
    return {
        "approval_id": approval.approval_id,
        "title": approval.title,
        "description": approval.description,
        "status": approval.status,
        "risk_level": approval.risk_level,
        "requested_by": approval.requested_by,
        "approver_id": approval.approver_id,
        "source_type": approval.source_type,
        "source_id": approval.source_id,
        "action_type": approval.action_type,
        "action_payload": json.loads(approval.action_payload_json or "{}"),
        "decision_note": approval.decision_note,
        "tenant_id": approval.tenant_id,
        "workspace_id": approval.workspace_id,
        "project_id": approval.project_id,
        "chat_channel": approval.chat_channel,
        "chat_message_id": approval.chat_message_id,
        "expires_at": approval.expires_at,
        "decided_at": approval.decided_at,
        "created_at": approval.created_at,
        "updated_at": approval.updated_at,
    }


def create_audit_event(
    db: Session,
    event_type: str,
    status: str,
    actor_id: Optional[str] = None,
    approval: Optional[PlatformApprovalRequest] = None,
    metadata: Optional[dict] = None,
) -> None:
    event = PlatformAuditEvent(
        event_type=event_type,
        actor_type="platform_admin" if actor_id else "system",
        actor_id=actor_id,
        tenant_id=approval.tenant_id if approval else None,
        workspace_id=approval.workspace_id if approval else None,
        project_id=approval.project_id if approval else None,
        status=status,
        route="/platform/approvals",
        auth_mode="platform_internal_token",
        metadata_json=json.dumps(metadata or {}),
    )
    db.add(event)


def get_approval_or_404(db: Session, approval_id: str) -> PlatformApprovalRequest:
    approval = (
        db.query(PlatformApprovalRequest)
        .filter(PlatformApprovalRequest.approval_id == approval_id)
        .first()
    )

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    return approval


def decide_approval(
    db: Session,
    approval_id: str,
    new_status: str,
    approver_id: str,
    decision_note: Optional[str] = None,
) -> dict:
    approval = get_approval_or_404(db, approval_id)

    if approval.status != PENDING_APPROVAL_STATUS:
        raise HTTPException(
            status_code=409,
            detail=f"Approval request is already {approval.status}",
        )

    now = utc_now()
    approval.status = new_status
    approval.approver_id = approver_id
    approval.decision_note = decision_note
    approval.decided_at = now
    approval.updated_at = now

    create_audit_event(
        db=db,
        event_type=f"approval_{new_status}",
        status=new_status,
        actor_id=approver_id,
        approval=approval,
        metadata={"approval_id": approval.approval_id, "decision_note": decision_note},
    )
    db.commit()
    db.refresh(approval)

    return approval_to_dict(approval)
