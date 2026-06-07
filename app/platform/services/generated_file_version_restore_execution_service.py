from __future__ import annotations

import json
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.platform.persistence.models import (
    PlatformApprovalRequest,
    PlatformGeneratedFile,
    PlatformGeneratedFileVersion,
    utc_now,
)
from app.platform.services.generated_file_version_restore_plan_service import (
    create_generated_file_version_restore_plan,
)


def _approval_to_dict(record: PlatformApprovalRequest) -> Dict[str, Any]:
    return {
        "approval_id": record.approval_id,
        "status": record.status,
        "source_type": record.source_type,
        "source_id": record.source_id,
        "action_type": record.action_type,
        "action_payload": json.loads(record.action_payload_json or "{}"),
        "workspace_id": record.workspace_id,
        "project_id": record.project_id,
        "decided_at": record.decided_at.isoformat() if record.decided_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def _not_executed_result(
    approval_id: str,
    reason: str,
    *,
    found: bool = True,
    approval: PlatformApprovalRequest | None = None,
) -> Dict[str, Any]:
    return {
        "success": True,
        "found": found,
        "approval_id": approval_id,
        "restore_mode": "db_restore_execution",
        "write_mode": "db_preview_only",
        "restore_execution_supported": True,
        "restore_execution_performed": False,
        "db_content_mutation_performed": False,
        "disk_write_performed": False,
        "generated_code_execution_performed": False,
        "reason": reason,
        "approval_request": _approval_to_dict(approval) if approval else None,
        "restore_result": None,
    }


def execute_approved_generated_file_version_restore(
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
            approval_id,
            "approval request not found",
            found=False,
        )

    if approval.status != "approved":
        return _not_executed_result(
            approval_id,
            "approval request is not approved",
            approval=approval,
        )

    if approval.source_type != "generated_file_version_restore_plan":
        return _not_executed_result(
            approval_id,
            "approval source type is not a generated file restore plan",
            approval=approval,
        )

    target_version_id = approval.source_id
    if not target_version_id:
        return _not_executed_result(
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
            approval_id,
            "restore plan target version or current file not found",
            approval=approval,
        )

    restore_plan = plan_result.get("restore_plan") or {}
    current_file_summary = restore_plan.get("current_file") or {}
    target_version_summary = restore_plan.get("target_version") or {}

    if current_file_summary.get("path") != target_version_summary.get("path"):
        return _not_executed_result(
            approval_id,
            "current file path does not match target version path",
            approval=approval,
        )

    if current_file_summary.get("language") != target_version_summary.get("language"):
        return _not_executed_result(
            approval_id,
            "current file language does not match target version language",
            approval=approval,
        )

    generated_file_id = current_file_summary.get("generated_file_id")
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

    if not generated_file or not target_version:
        return _not_executed_result(
            approval_id,
            "current generated file or target version record not found",
            approval=approval,
        )

    before_content_hash = generated_file.content_hash
    before_content_preview = generated_file.content_preview

    generated_file.content_preview = target_version.content_preview
    generated_file.content_hash = target_version.content_hash
    generated_file.updated_at = utc_now()

    target_version.restore_status = "restored"
    target_version.restored_at = utc_now()
    target_version.updated_at = utc_now()

    db.commit()
    db.refresh(generated_file)
    db.refresh(target_version)
    db.refresh(approval)

    restore_result = {
        "approval_id": approval_id,
        "target_version_id": target_version_id,
        "generated_file_id": generated_file.generated_file_id,
        "path": generated_file.path,
        "language": generated_file.language,
        "before_content_hash": before_content_hash,
        "after_content_hash": generated_file.content_hash,
        "before_content_preview": before_content_preview,
        "after_content_preview": generated_file.content_preview,
        "target_restore_status": target_version.restore_status,
        "restored_at": target_version.restored_at.isoformat()
        if target_version.restored_at
        else None,
    }

    return {
        "success": True,
        "found": True,
        "approval_id": approval_id,
        "target_version_id": target_version_id,
        "generated_file_id": generated_file.generated_file_id,
        "restore_mode": "db_restore_execution",
        "write_mode": "db_preview_only",
        "restore_execution_supported": True,
        "restore_execution_performed": True,
        "db_content_mutation_performed": True,
        "disk_write_performed": False,
        "generated_code_execution_performed": False,
        "approval_request": _approval_to_dict(approval),
        "restore_result": restore_result,
    }
