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

def execute_approved_generated_file_version_restore(
    db: Session,
    approval_id: str,
) -> Dict[str, Any]:
    plan_context = _load_restore_plan_or_block(db, approval_id)
    if "restore_result" in plan_context:
        return plan_context

    approval = plan_context["approval"]
    target_version_id = plan_context["target_version_id"]
    generated_file_id = plan_context["generated_file_id"]
    generated_file, target_version = _load_restore_records(
        db,
        generated_file_id=generated_file_id,
        target_version_id=target_version_id,
    )

    if not generated_file or not target_version:
        return _not_executed_result(
            db,
            approval_id,
            "current generated file or target version record not found",
            approval=approval,
        )

    before_content_hash = generated_file.content_hash
    before_content_preview = generated_file.content_preview

    pre_restore_snapshot = _create_pre_restore_snapshot(
        db,
        generated_file=generated_file,
        target_version=target_version,
        approval_id=approval_id,
        target_version_id=target_version_id,
        before_content_hash=before_content_hash,
    )

    generated_file.content_preview = target_version.content_preview
    generated_file.content_hash = target_version.content_hash
    generated_file.updated_at = utc_now()

    target_version.restore_status = "restored"
    target_version.restored_at = utc_now()
    target_version.updated_at = utc_now()

    execution_record = _record_restore_execution(
        db,
        approval_id=approval_id,
        target_version_id=target_version_id,
        generated_file_id=generated_file.generated_file_id,
        workflow_run_id=generated_file.workflow_run_id,
        workspace_id=generated_file.workspace_id,
        project_id=generated_file.project_id,
        execution_status="executed",
        reason="approved restore executed",
        before_content_hash=before_content_hash,
        after_content_hash=target_version.content_hash,
        target_content_hash=target_version.content_hash,
        before_content_preview=before_content_preview,
        after_content_preview=target_version.content_preview,
        restore_execution_performed=True,
        db_content_mutation_performed=True,
        disk_write_performed=False,
        generated_code_execution_performed=False,
    )

    post_restore_snapshot = _create_post_restore_snapshot(
        db,
        generated_file=generated_file,
        target_version=target_version,
        approval_id=approval_id,
        target_version_id=target_version_id,
        execution_record=execution_record,
    )

    db.commit()
    db.refresh(generated_file)
    db.refresh(target_version)
    db.refresh(approval)
    db.refresh(execution_record)

    restore_result = _build_restore_result(
        approval_id=approval_id,
        target_version_id=target_version_id,
        generated_file=generated_file,
        target_version=target_version,
        before_content_hash=before_content_hash,
        before_content_preview=before_content_preview,
        pre_restore_snapshot=pre_restore_snapshot,
        post_restore_snapshot=post_restore_snapshot,
    )

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
        "restore_execution_record": _execution_record_to_dict(execution_record),
        "pre_restore_snapshot": pre_restore_snapshot,
        "post_restore_snapshot": post_restore_snapshot,
        "restore_result": restore_result,
    }
