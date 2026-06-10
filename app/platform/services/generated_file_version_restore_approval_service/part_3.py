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

def approve_generated_file_version_restore_approval_request(
    db: Session,
    approval_id: str,
    approver_id: str = "platform_admin",
    decision_note: Optional[str] = None,
) -> Dict[str, Any]:
    return decide_generated_file_version_restore_approval_request(
        db,
        approval_id=approval_id,
        decision="approved",
        approver_id=approver_id,
        decision_note=decision_note,
    )

def reject_generated_file_version_restore_approval_request(
    db: Session,
    approval_id: str,
    approver_id: str = "platform_admin",
    decision_note: Optional[str] = None,
) -> Dict[str, Any]:
    return decide_generated_file_version_restore_approval_request(
        db,
        approval_id=approval_id,
        decision="rejected",
        approver_id=approver_id,
        decision_note=decision_note,
    )
