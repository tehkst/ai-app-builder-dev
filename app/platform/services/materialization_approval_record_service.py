from __future__ import annotations

import json
from typing import Any, Dict
from uuid import uuid4

from sqlalchemy.orm import Session

from app.platform.persistence.models import (
    PlatformGeneratedFile,
    PlatformMaterializationApprovalRecord,
    utc_now,
)


def _record_to_dict(record: PlatformMaterializationApprovalRecord) -> Dict[str, Any]:
    return {
        "materialization_approval_record_id": record.materialization_approval_record_id,
        "generated_file_id": record.generated_file_id,
        "workflow_run_id": record.workflow_run_id,
        "workspace_id": record.workspace_id,
        "project_id": record.project_id,
        "selected_path": record.selected_path,
        "approval_status": record.approval_status,
        "approval_action": record.approval_action,
        "approval_token": record.approval_token,
        "approved_by": record.approved_by,
        "approval_reason": record.approval_reason,
        "safety_mode": record.safety_mode,
        "approval_record_only": record.approval_record_only,
        "approval_grants_filesystem_write_capability": record.approval_grants_filesystem_write_capability,
        "materialization_execution_enabled": record.materialization_execution_enabled,
        "generated_files_written_to_disk": record.generated_files_written_to_disk,
        "filesystem_write_performed": record.filesystem_write_performed,
        "disk_write_performed": record.disk_write_performed,
        "runtime_server_started": record.runtime_server_started,
        "preview_server_started": record.preview_server_started,
        "generated_code_execution_performed": record.generated_code_execution_performed,
        "repair_applied": record.repair_applied,
        "restore_executed": record.restore_executed,
        "metadata": json.loads(record.metadata_json or "{}"),
        "approved_at": record.approved_at.isoformat() if record.approved_at else None,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def create_materialization_approval_record(
    db: Session,
    generated_file_id: str,
    approved_by: str = "platform_admin",
    approval_reason: str = None,
) -> Dict[str, Any]:
    generated_file = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.generated_file_id == generated_file_id)
        .first()
    )

    if not generated_file:
        return {
            "success": True,
            "found": False,
            "record_created": False,
            "generated_file_id": generated_file_id,
            "safety_mode": "persistent_record_only_no_write_capability",
            "approval_record_only": True,
            "approval_grants_filesystem_write_capability": False,
            "materialization_execution_enabled": False,
            "generated_files_written_to_disk": False,
            "filesystem_write_performed": False,
            "disk_write_performed": False,
            "runtime_server_started": False,
            "preview_server_started": False,
            "generated_code_execution_performed": False,
            "repair_applied": False,
            "restore_executed": False,
            "approval_record": None,
        }

    approval_token = "materialization-approval-record-" + uuid4().hex
    now = utc_now()
    record = PlatformMaterializationApprovalRecord(
        materialization_approval_record_id="materialization_approval_" + uuid4().hex,
        generated_file_id=generated_file.generated_file_id,
        workflow_run_id=generated_file.workflow_run_id,
        workspace_id=generated_file.workspace_id,
        project_id=generated_file.project_id,
        selected_path=generated_file.path,
        approval_status="approved",
        approval_action="approve",
        approval_token=approval_token,
        approved_by=approved_by,
        approval_reason=approval_reason
        or "Approval granted for V90 static preview materialization into the guarded local sandbox only.",
        safety_mode="approval_gated_static_preview_materialization",
        approval_record_only=False,
        approval_grants_filesystem_write_capability=True,
        materialization_execution_enabled=True,
        generated_files_written_to_disk=False,
        filesystem_write_performed=False,
        disk_write_performed=False,
        runtime_server_started=False,
        preview_server_started=False,
        generated_code_execution_performed=False,
        repair_applied=False,
        restore_executed=False,
        metadata_json=json.dumps(
            {
                "source": "v90_approval_gated_static_preview_materialization",
                "write_mode": "approval_gated_static_preview_materialization",
                "execution_supported": True,
                "materialization_execution_supported": True,
                "static_preview_materialization_only": True,
            },
            sort_keys=True,
        ),
        approved_at=now,
        created_at=now,
        updated_at=now,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "success": True,
        "found": True,
        "record_created": True,
        "generated_file_id": generated_file.generated_file_id,
        "safety_mode": "approval_gated_static_preview_materialization",
        "approval_record_only": False,
        "approval_grants_filesystem_write_capability": True,
        "materialization_execution_enabled": True,
        "generated_files_written_to_disk": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "generated_code_execution_performed": False,
        "repair_applied": False,
        "restore_executed": False,
        "approval_record": _record_to_dict(record),
    }


def get_latest_materialization_approval_record(
    db: Session,
    generated_file_id: str,
) -> Dict[str, Any]:
    record = (
        db.query(PlatformMaterializationApprovalRecord)
        .filter(PlatformMaterializationApprovalRecord.generated_file_id == generated_file_id)
        .order_by(PlatformMaterializationApprovalRecord.created_at.desc())
        .first()
    )

    if not record:
        return {
            "success": True,
            "found": False,
            "generated_file_id": generated_file_id,
            "safety_mode": "persistent_record_only_no_write_capability",
            "approval_record_only": True,
            "approval_grants_filesystem_write_capability": False,
            "materialization_execution_enabled": False,
            "generated_files_written_to_disk": False,
            "filesystem_write_performed": False,
            "disk_write_performed": False,
            "runtime_server_started": False,
            "preview_server_started": False,
            "generated_code_execution_performed": False,
            "repair_applied": False,
            "restore_executed": False,
            "approval_record": None,
        }

    return {
        "success": True,
        "found": True,
        "generated_file_id": generated_file_id,
        "safety_mode": "persistent_record_only_no_write_capability",
        "approval_record_only": True,
        "approval_grants_filesystem_write_capability": False,
        "materialization_execution_enabled": False,
        "generated_files_written_to_disk": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "generated_code_execution_performed": False,
        "repair_applied": False,
        "restore_executed": False,
        "approval_record": _record_to_dict(record),
    }
