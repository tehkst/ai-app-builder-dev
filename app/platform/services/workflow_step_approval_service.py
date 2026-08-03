from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformApprovalRequest, utc_now
from app.platform.services.approval_service import approval_to_dict, create_audit_event

SOURCE_TYPE_WORKFLOW_STEP = "workflow_step"


def create_step_approval_request(
    db: Session,
    *,
    workflow_run_id: str,
    step_run: Dict[str, Any],
    handler_result: Dict[str, Any],
    scoping_request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist a real founder decision request for a step that escalated.

    Reuses PlatformApprovalRequest (already the right grain - one row per thing
    needing a decision, with source_type/source_id for polymorphic linking) and
    approval_service.py's audit-event helper, rather than a bespoke table. Not
    the existing /platform/approvals/* routes (those are require_platform_admin
    -gated; a customer's own build needs the customer's own decision), just the
    model and these two functions - see plan for the full reuse rationale.
    """
    now = utc_now()
    approval = PlatformApprovalRequest(
        approval_id="apr_step_%s" % uuid.uuid4().hex[:16],
        title="%s needs a decision" % (step_run.get("title") or step_run.get("step_id")),
        description=str(handler_result.get("rationale") or ""),
        status="pending",
        risk_level="medium",
        requested_by=str(handler_result.get("agent_id") or "management_agent"),
        source_type=SOURCE_TYPE_WORKFLOW_STEP,
        source_id=str(step_run.get("step_run_id")),
        action_type=str(handler_result.get("decision") or "escalate"),
        action_payload_json=json.dumps(
            {
                "workflow_run_id": workflow_run_id,
                "step_id": step_run.get("step_id"),
                "handler_result": handler_result,
            },
            default=str,
        ),
        project_id=scoping_request_id,
        created_at=now,
        updated_at=now,
    )
    db.add(approval)
    create_audit_event(
        db=db,
        event_type="workflow_step_escalated",
        status="pending",
        approval=approval,
        metadata={
            "workflow_run_id": workflow_run_id,
            "step_id": step_run.get("step_id"),
            "step_run_id": step_run.get("step_run_id"),
        },
    )
    db.commit()
    db.refresh(approval)
    return approval_to_dict(approval)


def get_step_approval_request(db: Session, *, step_run_id: str) -> Optional[Dict[str, Any]]:
    approval = (
        db.query(PlatformApprovalRequest)
        .filter(
            PlatformApprovalRequest.source_type == SOURCE_TYPE_WORKFLOW_STEP,
            PlatformApprovalRequest.source_id == step_run_id,
        )
        .order_by(PlatformApprovalRequest.id.desc())
        .first()
    )
    return approval_to_dict(approval) if approval else None
