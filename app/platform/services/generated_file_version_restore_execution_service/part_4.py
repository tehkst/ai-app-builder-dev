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

def _create_pre_restore_snapshot(
    db: Session,
    *,
    generated_file: PlatformGeneratedFile,
    target_version: PlatformGeneratedFileVersion,
    approval_id: str,
    target_version_id: str,
    before_content_hash: str,
) -> Dict[str, Any]:
    return create_generated_file_version_snapshot(
        db,
        generated_file.generated_file_id,
        snapshot_status="pre_restore_rollback_snapshot",
        restore_status="rollback_point",
        metadata={
            "snapshot_reason": "pre_restore_rollback_safety",
            "source_restore_approval_id": approval_id,
            "source_target_version_id": target_version_id,
            "current_content_hash_before_restore": before_content_hash,
            "target_content_hash": target_version.content_hash,
            "restore_execution_performed": False,
            "db_content_mutation_performed": False,
            "disk_write_performed": False,
            "generated_code_execution_performed": False,
        },
        commit=False,
    )

def _create_post_restore_snapshot(
    db: Session,
    *,
    generated_file: PlatformGeneratedFile,
    target_version: PlatformGeneratedFileVersion,
    approval_id: str,
    target_version_id: str,
    execution_record: PlatformGeneratedFileRestoreExecution,
) -> Dict[str, Any]:
    return create_generated_file_version_snapshot(
        db,
        generated_file.generated_file_id,
        snapshot_status="restore_snapshot",
        restore_status="restore_result",
        metadata={
            "snapshot_reason": "post_restore_snapshot",
            "source_restore_approval_id": approval_id,
            "source_restore_execution_id": execution_record.restore_execution_id,
            "source_target_version_id": target_version_id,
            "source_target_content_hash": target_version.content_hash,
            "restore_execution_performed": True,
            "db_content_mutation_performed": True,
            "disk_write_performed": False,
            "generated_code_execution_performed": False,
        },
        commit=False,
    )

def _build_restore_result(
    *,
    approval_id: str,
    target_version_id: str,
    generated_file: PlatformGeneratedFile,
    target_version: PlatformGeneratedFileVersion,
    before_content_hash: str,
    before_content_preview: str,
    pre_restore_snapshot: Dict[str, Any],
    post_restore_snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    return {
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
        "pre_restore_snapshot_created": pre_restore_snapshot.get("snapshot_created"),
        "pre_restore_snapshot_version_id": pre_restore_snapshot.get(
            "generated_file_version_id"
        ),
        "pre_restore_snapshot_version_number": pre_restore_snapshot.get(
            "version_number"
        ),
        "post_restore_snapshot_created": post_restore_snapshot.get("snapshot_created"),
        "post_restore_snapshot_version_id": post_restore_snapshot.get(
            "generated_file_version_id"
        ),
        "post_restore_snapshot_version_number": post_restore_snapshot.get(
            "version_number"
        ),
    }
