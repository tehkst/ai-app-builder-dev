# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import json
from typing import Any, Dict, Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from app.platform.persistence.models import PlatformApprovalRequest
from app.platform.services.generated_file_version_restore_plan_service import (
    create_generated_file_version_restore_plan,
)

def get_generated_file_version_restore_approval_request(
    db: Session,
    approval_id: str,
) -> Dict[str, Any]:
    approval = (
        db.query(PlatformApprovalRequest)
        .filter(PlatformApprovalRequest.approval_id == approval_id)
        .first()
    )

    if not approval:
        return {
            "success": True,
            "found": False,
            "approval_id": approval_id,
            "restore_mode": "approval_only",
            "write_mode": "db_preview_only",
            "disk_write_performed": False,
            "db_content_mutation_performed": False,
            "restore_execution_performed": False,
            "approval_request": None,
        }

    return {
        "success": True,
        "found": True,
        "approval_id": approval_id,
        "restore_mode": "approval_only",
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "db_content_mutation_performed": False,
        "restore_execution_performed": False,
        "approval_request": _approval_to_dict(approval),
    }

def decide_generated_file_version_restore_approval_request(
    db: Session,
    approval_id: str,
    decision: str,
    approver_id: str = "platform_admin",
    decision_note: Optional[str] = None,
) -> Dict[str, Any]:
    if decision not in {"approved", "rejected"}:
        return {
            "success": False,
            "found": False,
            "approval_id": approval_id,
            "error": "decision must be approved or rejected",
            "restore_mode": "approval_decision_only",
            "write_mode": "db_preview_only",
            "disk_write_performed": False,
            "db_content_mutation_performed": False,
            "restore_execution_performed": False,
            "approval_request": None,
        }

    approval = (
        db.query(PlatformApprovalRequest)
        .filter(PlatformApprovalRequest.approval_id == approval_id)
        .first()
    )

    if not approval:
        return {
            "success": True,
            "found": False,
            "approval_id": approval_id,
            "decision": decision,
            "restore_mode": "approval_decision_only",
            "write_mode": "db_preview_only",
            "disk_write_performed": False,
            "db_content_mutation_performed": False,
            "restore_execution_performed": False,
            "approval_request": None,
        }

    if approval.status != "pending":
        return {
            "success": True,
            "found": True,
            "approval_id": approval_id,
            "decision": decision,
            "decision_applied": False,
            "reason": "approval request is no longer pending",
            "restore_mode": "approval_decision_only",
            "write_mode": "db_preview_only",
            "disk_write_performed": False,
            "db_content_mutation_performed": False,
            "restore_execution_performed": False,
            "approval_request": _approval_to_dict(approval),
        }

    from app.platform.persistence.models import utc_now

    approval.status = decision
    approval.approver_id = approver_id
    approval.decision_note = decision_note or (
        "Approved restore plan without executing restore."
        if decision == "approved"
        else "Rejected restore plan without executing restore."
    )
    approval.decided_at = utc_now()
    approval.updated_at = utc_now()

    db.commit()
    db.refresh(approval)

    return {
        "success": True,
        "found": True,
        "approval_id": approval_id,
        "decision": decision,
        "decision_applied": True,
        "restore_mode": "approval_decision_only",
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "db_content_mutation_performed": False,
        "restore_execution_performed": False,
        "approval_request": _approval_to_dict(approval),
    }
