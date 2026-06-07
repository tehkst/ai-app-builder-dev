from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.materialization_approval_record_service import (
    get_latest_materialization_approval_record,
)


def check_materialization_execution_gate(
    db: Session,
    generated_file_id: str,
) -> Dict[str, Any]:
    generated_file = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.generated_file_id == generated_file_id)
        .first()
    )

    approval_result = get_latest_materialization_approval_record(
        db,
        generated_file_id=generated_file_id,
    )

    approval_record = approval_result.get("approval_record")
    approval_found = bool(approval_result.get("found"))

    if not generated_file:
        block_reason = "Generated file was not found in DB preview storage."
    elif not approval_found:
        block_reason = "No persistent materialization approval record exists for this generated file."
    else:
        block_reason = "Persistent approval record exists, but V62 keeps materialization execution disabled."

    return {
        "success": True,
        "found": bool(generated_file),
        "generated_file_id": generated_file_id,
        "workflow_run_id": generated_file.workflow_run_id if generated_file else None,
        "workspace_id": generated_file.workspace_id if generated_file else None,
        "project_id": generated_file.project_id if generated_file else None,
        "selected_path": generated_file.path if generated_file else None,
        "approval_found": approval_found,
        "approval_record": approval_record,
        "execution_gate_status": "blocked",
        "block_reason": block_reason,
        "safety_mode": "materialization_execution_gate_blocked_no_write",
        "execution_gate_only": True,
        "approval_checked": True,
        "approval_required_before_execution": True,
        "approval_record_grants_execution": False,
        "materialization_execution_enabled": False,
        "materialization_execution_attempted": True,
        "materialization_execution_performed": False,
        "generated_files_written_to_disk": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "generated_code_execution_performed": False,
        "repair_applied": False,
        "restore_executed": False,
    }


def attempt_materialization_execution(
    db: Session,
    generated_file_id: str,
) -> Dict[str, Any]:
    result = check_materialization_execution_gate(
        db,
        generated_file_id=generated_file_id,
    )

    result["execution_attempt_recorded"] = True
    result["execution_attempt_result"] = "blocked_no_write"
    result["write_mode"] = "db_preview_only"
    result["message"] = (
        "Materialization execution attempt was blocked by V62 gate. "
        "No files were written, no generated code was executed, and no servers were started."
    )

    return result
