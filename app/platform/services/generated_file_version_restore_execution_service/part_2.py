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
