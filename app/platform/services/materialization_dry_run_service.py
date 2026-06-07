from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.materialization_approval_record_service import (
    get_latest_materialization_approval_record,
)
from app.platform.services.materialization_execution_gate_service import (
    check_materialization_execution_gate,
)


def _normalize_relative_path(path: str) -> str:
    raw = (path or "").replace("\\", "/").strip()
    parts = []

    for part in raw.split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            continue
        parts.append(part)

    cleaned = "/".join(parts)
    return cleaned or "generated-file.txt"


def _dry_run_file_to_dict(generated_file: PlatformGeneratedFile) -> Dict[str, Any]:
    safe_relative_path = _normalize_relative_path(generated_file.path)
    dry_run_target_path = "approved-sandbox-workspace/" + safe_relative_path

    return {
        "generated_file_id": generated_file.generated_file_id,
        "workflow_run_id": generated_file.workflow_run_id,
        "workspace_id": generated_file.workspace_id,
        "project_id": generated_file.project_id,
        "source_path": generated_file.path,
        "safe_relative_path": safe_relative_path,
        "dry_run_target_path": dry_run_target_path,
        "language": generated_file.language,
        "purpose": generated_file.purpose,
        "content_hash": generated_file.content_hash,
        "content_preview_length": len(generated_file.content_preview or ""),
        "write_status": generated_file.write_status,
        "would_write": True,
        "write_performed": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "generated_code_execution_performed": False,
    }


def build_materialization_dry_run(
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
    execution_gate = check_materialization_execution_gate(
        db,
        generated_file_id=generated_file_id,
    )

    dry_run_files: List[Dict[str, Any]] = []
    if generated_file:
        dry_run_files.append(_dry_run_file_to_dict(generated_file))

    if not generated_file:
        dry_run_status = "blocked"
        block_reason = "Generated file was not found in DB preview storage."
    else:
        dry_run_status = "planned"
        block_reason = (
            "Dry-run plan created only. V63 does not write files, execute generated code, "
            "or start any runtime or preview server."
        )

    return {
        "success": True,
        "found": bool(generated_file),
        "generated_file_id": generated_file_id,
        "workflow_run_id": generated_file.workflow_run_id if generated_file else None,
        "workspace_id": generated_file.workspace_id if generated_file else None,
        "project_id": generated_file.project_id if generated_file else None,
        "selected_path": generated_file.path if generated_file else None,
        "dry_run_status": dry_run_status,
        "block_reason": block_reason,
        "safety_mode": "safe_workspace_materialization_dry_run_only",
        "write_mode": "db_preview_only",
        "dry_run_only": True,
        "would_write_file_count": len(dry_run_files),
        "dry_run_files": dry_run_files,
        "approval_found": bool(approval_result.get("found")),
        "approval_record": approval_result.get("approval_record"),
        "execution_gate_status": execution_gate.get("execution_gate_status"),
        "execution_gate_result": execution_gate,
        "materialization_execution_enabled": False,
        "materialization_execution_performed": False,
        "generated_files_written_to_disk": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "generated_code_execution_performed": False,
        "repair_applied": False,
        "restore_executed": False,
        "message": (
            "Safe workspace materialization dry run completed. "
            "No files were written, no generated code was executed, and no servers were started."
        ),
    }
