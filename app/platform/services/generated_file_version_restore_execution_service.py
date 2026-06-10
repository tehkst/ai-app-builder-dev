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


def _record_restore_execution(
    db: Session,
    *,
    approval_id: Optional[str],
    target_version_id: Optional[str] = None,
    generated_file_id: Optional[str] = None,
    workflow_run_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    project_id: Optional[str] = None,
    execution_status: str,
    reason: Optional[str] = None,
    before_content_hash: Optional[str] = None,
    after_content_hash: Optional[str] = None,
    target_content_hash: Optional[str] = None,
    before_content_preview: Optional[str] = None,
    after_content_preview: Optional[str] = None,
    restore_execution_performed: bool = False,
    db_content_mutation_performed: bool = False,
    disk_write_performed: bool = False,
    generated_code_execution_performed: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> PlatformGeneratedFileRestoreExecution:
    record = PlatformGeneratedFileRestoreExecution(
        restore_execution_id=f"restore_execution_{uuid4().hex}",
        approval_id=approval_id,
        target_version_id=target_version_id,
        generated_file_id=generated_file_id,
        workflow_run_id=workflow_run_id,
        workspace_id=workspace_id,
        project_id=project_id,
        execution_status=execution_status,
        reason=reason,
        before_content_hash=before_content_hash,
        after_content_hash=after_content_hash,
        target_content_hash=target_content_hash,
        before_content_preview=before_content_preview,
        after_content_preview=after_content_preview,
        restore_execution_performed=restore_execution_performed,
        db_content_mutation_performed=db_content_mutation_performed,
        disk_write_performed=disk_write_performed,
        generated_code_execution_performed=generated_code_execution_performed,
        metadata_json=json.dumps(metadata or {}, sort_keys=True),
    )
    db.add(record)
    db.flush()
    return record


def _execution_record_to_dict(
    record: Optional[PlatformGeneratedFileRestoreExecution],
) -> Optional[Dict[str, Any]]:
    if not record:
        return None

    return {
        "restore_execution_id": record.restore_execution_id,
        "approval_id": record.approval_id,
        "target_version_id": record.target_version_id,
        "generated_file_id": record.generated_file_id,
        "workflow_run_id": record.workflow_run_id,
        "workspace_id": record.workspace_id,
        "project_id": record.project_id,
        "execution_status": record.execution_status,
        "reason": record.reason,
        "before_content_hash": record.before_content_hash,
        "after_content_hash": record.after_content_hash,
        "target_content_hash": record.target_content_hash,
        "restore_mode": record.restore_mode,
        "write_mode": record.write_mode,
        "restore_execution_performed": record.restore_execution_performed,
        "db_content_mutation_performed": record.db_content_mutation_performed,
        "disk_write_performed": record.disk_write_performed,
        "generated_code_execution_performed": record.generated_code_execution_performed,
        "executed_at": record.executed_at.isoformat() if record.executed_at else None,
    }


def _not_executed_result(
    db: Session,
    approval_id: str,
    reason: str,
    *,
    found: bool = True,
    approval: Optional[PlatformApprovalRequest] = None,
    target_version_id: Optional[str] = None,
    generated_file_id: Optional[str] = None,
    workflow_run_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    resolved_target_version_id = target_version_id
    resolved_workspace_id = workspace_id
    resolved_project_id = project_id

    if approval:
        resolved_target_version_id = resolved_target_version_id or approval.source_id
        resolved_workspace_id = resolved_workspace_id or approval.workspace_id
        resolved_project_id = resolved_project_id or approval.project_id

    execution_record = _record_restore_execution(
        db,
        approval_id=approval_id,
        target_version_id=resolved_target_version_id,
        generated_file_id=generated_file_id,
        workflow_run_id=workflow_run_id,
        workspace_id=resolved_workspace_id,
        project_id=resolved_project_id,
        execution_status="blocked",
        reason=reason,
        restore_execution_performed=False,
        db_content_mutation_performed=False,
        disk_write_performed=False,
        generated_code_execution_performed=False,
    )
    db.commit()
    db.refresh(execution_record)

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
        "restore_execution_record": _execution_record_to_dict(execution_record),
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
    current_file_summary = restore_plan.get("current_file") or {}
    target_version_summary = restore_plan.get("target_version") or {}

    if current_file_summary.get("path") != target_version_summary.get("path"):
        return _not_executed_result(
            db,
            approval_id,
            "current file path does not match target version path",
            approval=approval,
        )

    if current_file_summary.get("language") != target_version_summary.get("language"):
        return _not_executed_result(
            db,
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
            db,
            approval_id,
            "current generated file or target version record not found",
            approval=approval,
        )

    before_content_hash = generated_file.content_hash
    before_content_preview = generated_file.content_preview

    pre_restore_snapshot = create_generated_file_version_snapshot(
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

    post_restore_snapshot = create_generated_file_version_snapshot(
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

    db.commit()
    db.refresh(generated_file)
    db.refresh(target_version)
    db.refresh(approval)
    db.refresh(execution_record)

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
