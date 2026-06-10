# Split from restore execution service.
from __future__ import annotations
import json
from uuid import uuid4
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.platform.persistence.models import (
    PlatformApprovalRequest,
    PlatformGeneratedFile,
    PlatformGeneratedFileVersion,
    PlatformGeneratedFileRestoreExecution,
    utc_now,
)
from app.platform.services.generated_file_version_restore_plan_service import (
    create_generated_file_version_restore_plan,
)
from app.platform.services.generated_file_version_service import (
    create_generated_file_version_snapshot,
)

def _load_restore_plan_or_block(
    db: Session,
    approval_id: str,
) -> Dict[str, Any]:
    approval = (
        db.query(PlatformApprovalRequest)
        .filter(PlatformApprovalRequest.approval_id == approval_id)
        .first()
    )

    if not approval:
        return _not_executed_result(
            db,
            approval_id,
            "approval request not found",
            found=False,
        )

    if approval.status != "approved":
        return _not_executed_result(
            db,
            approval_id,
            "approval request is not approved",
            approval=approval,
        )

    if approval.source_type != "generated_file_version_restore_plan":
        return _not_executed_result(
            db,
            approval_id,
            "approval source type is not a generated file restore plan",
            approval=approval,
        )

    target_version_id = approval.source_id
    if not target_version_id:
        return _not_executed_result(
            db,
            approval_id,
            "approval source_id does not contain target version id",
            approval=approval,
        )

    plan_result = create_generated_file_version_restore_plan(
        db,
        target_version_id=target_version_id,
    )

    if not plan_result.get("found"):
        return _not_executed_result(
            db,
            approval_id,
            "restore plan target version or current file not found",
            approval=approval,
        )

    restore_plan = plan_result.get("restore_plan") or {}
    current_summary = restore_plan.get("current_file") or {}
    target_summary = restore_plan.get("target_version") or {}

    if current_summary.get("path") != target_summary.get("path"):
        return _not_executed_result(
            db,
            approval_id,
            "current file path does not match target version path",
            approval=approval,
        )

    if current_summary.get("language") != target_summary.get("language"):
        return _not_executed_result(
            db,
            approval_id,
            "current file language does not match target version language",
            approval=approval,
        )

    return {
        "success": True,
        "approval": approval,
        "target_version_id": target_version_id,
        "generated_file_id": current_summary.get("generated_file_id"),
    }

def _load_restore_records(
    db: Session,
    *,
    generated_file_id: str,
    target_version_id: str,
):
    generated_file = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.generated_file_id == generated_file_id)
        .first()
    )

    target_version = (
        db.query(PlatformGeneratedFileVersion)
        .filter(
            PlatformGeneratedFileVersion.generated_file_version_id
            == target_version_id
        )
        .first()
    )

    return generated_file, target_version
