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
