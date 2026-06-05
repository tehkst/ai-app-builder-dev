import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.dashboard.approval_dashboard import APPROVAL_DASHBOARD_HTML
from app.platform.persistence.database import get_platform_db
from app.platform.persistence.models import PlatformApprovalRequest, utc_now
from app.platform.security.rate_limit import PLATFORM_API_RATE_LIMIT, limiter
from app.platform.services.approval_service import (
    PENDING_APPROVAL_STATUS,
    approval_to_dict,
    create_audit_event,
    decide_approval,
    get_approval_or_404,
)

router = APIRouter(prefix="/platform", tags=["platform-approvals"])


class ApprovalCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    risk_level: str = "medium"
    requested_by: str = "ai_agent"
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    action_type: Optional[str] = None
    action_payload: Optional[dict] = None
    tenant_id: Optional[str] = None
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    chat_channel: Optional[str] = None
    chat_message_id: Optional[str] = None


class ApprovalDecisionRequest(BaseModel):
    approver_id: str = "platform_admin"
    decision_note: Optional[str] = None


def clamp_limit(limit: int) -> int:
    if limit < 1:
        return 1
    if limit > 100:
        return 100
    return limit


@router.get("/dashboard/approvals", response_class=HTMLResponse)
def approval_dashboard():
    return HTMLResponse(APPROVAL_DASHBOARD_HTML)


@router.post("/approvals")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def create_approval_request(
    request: Request,
    payload: ApprovalCreateRequest,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    now = utc_now()
    approval = PlatformApprovalRequest(
        approval_id=f"apr_{uuid.uuid4().hex[:16]}",
        title=payload.title,
        description=payload.description,
        status=PENDING_APPROVAL_STATUS,
        risk_level=payload.risk_level,
        requested_by=payload.requested_by,
        source_type=payload.source_type,
        source_id=payload.source_id,
        action_type=payload.action_type,
        action_payload_json=json.dumps(payload.action_payload or {}),
        tenant_id=payload.tenant_id,
        workspace_id=payload.workspace_id,
        project_id=payload.project_id,
        chat_channel=payload.chat_channel,
        chat_message_id=payload.chat_message_id,
        created_at=now,
        updated_at=now,
    )
    db.add(approval)
    create_audit_event(
        db=db,
        event_type="approval_created",
        status=PENDING_APPROVAL_STATUS,
        approval=approval,
        metadata={"approval_id": approval.approval_id, "title": approval.title},
    )
    db.commit()
    db.refresh(approval)
    return approval_to_dict(approval)


@router.get("/approvals")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_approval_requests(
    request: Request,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    safe_limit = clamp_limit(limit)
    query = db.query(PlatformApprovalRequest)
    if status:
        query = query.filter(PlatformApprovalRequest.status == status)
    approvals = query.order_by(PlatformApprovalRequest.id.desc()).limit(safe_limit).all()
    return {
        "items": [approval_to_dict(approval) for approval in approvals],
        "limit": safe_limit,
        "status": status,
    }


@router.get("/approvals/{approval_id}")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def get_approval_request(
    request: Request,
    approval_id: str,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    return approval_to_dict(get_approval_or_404(db, approval_id))


@router.post("/approvals/{approval_id}/approve")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def approve_approval_request(
    request: Request,
    approval_id: str,
    decision: ApprovalDecisionRequest,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    return decide_approval(
        db=db,
        approval_id=approval_id,
        new_status="approved",
        approver_id=decision.approver_id,
        decision_note=decision.decision_note,
    )


@router.post("/approvals/{approval_id}/reject")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def reject_approval_request(
    request: Request,
    approval_id: str,
    decision: ApprovalDecisionRequest,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    return decide_approval(
        db=db,
        approval_id=approval_id,
        new_status="rejected",
        approver_id=decision.approver_id,
        decision_note=decision.decision_note,
    )


@router.post("/approvals/{approval_id}/request-changes")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def request_approval_changes(
    request: Request,
    approval_id: str,
    decision: ApprovalDecisionRequest,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    return decide_approval(
        db=db,
        approval_id=approval_id,
        new_status="changes_requested",
        approver_id=decision.approver_id,
        decision_note=decision.decision_note,
    )
