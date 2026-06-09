from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.platform.guards.filesystem_write_guard import validate_generated_file_write_path
from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.materialization_approval_record_service import (
    get_latest_materialization_approval_record,
)


APPROVED_SANDBOX_ROOT_BASE = Path("/tmp/ai-software-factory/workspaces")


APPROVED_STATIC_PREVIEW_EXTENSIONS = {".html", ".css", ".js", ".md", ".json", ".txt"}


def _is_static_preview_file(path: str) -> bool:
    return Path(path or "").suffix.lower() in APPROVED_STATIC_PREVIEW_EXTENSIONS


def _safe_workspace_root(workspace_id: str) -> str:
    safe_workspace_id = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-"
        for char in (workspace_id or "unknown-workspace")
    ).strip("-")

    if not safe_workspace_id:
        safe_workspace_id = "unknown-workspace"

    return str(APPROVED_SANDBOX_ROOT_BASE / safe_workspace_id)


def write_generated_file_to_local_sandbox(
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

    if not generated_file:
        return {
            "success": True,
            "found": False,
            "generated_file_id": generated_file_id,
            "write_status": "blocked",
            "block_reason": "Generated file was not found in DB preview storage.",
            "safety_mode": "approval_gated_static_preview_materialization",
            "sandbox_write_enabled": False,
            "approval_found": bool(approval_result.get("found")),
            "workspace_root": None,
            "target_path": None,
            "filesystem_write_performed": False,
            "disk_write_performed": False,
            "generated_files_written_to_disk": False,
            "generated_code_execution_performed": False,
            "runtime_server_started": False,
            "preview_server_started": False,
            "external_deployment_performed": False,
            "repair_applied": False,
            "restore_executed": False,
        }

    if not approval_result.get("found"):
        return {
            "success": True,
            "found": True,
            "generated_file_id": generated_file.generated_file_id,
            "workflow_run_id": generated_file.workflow_run_id,
            "workspace_id": generated_file.workspace_id,
            "project_id": generated_file.project_id,
            "selected_path": generated_file.path,
            "write_status": "blocked",
            "block_reason": "Persistent approval record is required before sandbox materialization.",
            "safety_mode": "approval_gated_static_preview_materialization",
            "sandbox_write_enabled": False,
            "approval_found": False,
            "workspace_root": _safe_workspace_root(generated_file.workspace_id),
            "target_path": None,
            "filesystem_write_performed": False,
            "disk_write_performed": False,
            "generated_files_written_to_disk": False,
            "generated_code_execution_performed": False,
            "runtime_server_started": False,
            "preview_server_started": False,
            "external_deployment_performed": False,
            "repair_applied": False,
            "restore_executed": False,
        }

    approval_record = approval_result.get("approval_record") or {}
    approval_grants_write = bool(approval_record.get("approval_grants_filesystem_write_capability"))
    materialization_enabled = bool(approval_record.get("materialization_execution_enabled"))

    if not approval_grants_write or not materialization_enabled:
        return {
            "success": True,
            "found": True,
            "generated_file_id": generated_file.generated_file_id,
            "workflow_run_id": generated_file.workflow_run_id,
            "workspace_id": generated_file.workspace_id,
            "project_id": generated_file.project_id,
            "selected_path": generated_file.path,
            "write_status": "blocked",
            "block_reason": "Approval record does not grant V90 static preview materialization capability.",
            "safety_mode": "approval_gated_static_preview_materialization",
            "sandbox_write_enabled": False,
            "approval_found": True,
            "approval_record": approval_record,
            "workspace_root": str(_safe_workspace_root(generated_file.workspace_id)),
            "target_path": None,
            "filesystem_write_performed": False,
            "disk_write_performed": False,
            "generated_files_written_to_disk": False,
            "generated_code_execution_performed": False,
            "runtime_server_started": False,
            "preview_server_started": False,
            "external_deployment_performed": False,
            "repair_applied": False,
            "restore_executed": False,
        }

    if not _is_static_preview_file(generated_file.path):
        return {
            "success": True,
            "found": True,
            "generated_file_id": generated_file.generated_file_id,
            "workflow_run_id": generated_file.workflow_run_id,
            "workspace_id": generated_file.workspace_id,
            "project_id": generated_file.project_id,
            "selected_path": generated_file.path,
            "write_status": "blocked",
            "block_reason": "Only static preview files are eligible for V90 materialization.",
            "safety_mode": "approval_gated_static_preview_materialization",
            "sandbox_write_enabled": False,
            "approval_found": True,
            "approval_record": approval_record,
            "workspace_root": str(_safe_workspace_root(generated_file.workspace_id)),
            "target_path": None,
            "allowed_static_preview_extensions": sorted(APPROVED_STATIC_PREVIEW_EXTENSIONS),
            "filesystem_write_performed": False,
            "disk_write_performed": False,
            "generated_files_written_to_disk": False,
            "generated_code_execution_performed": False,
            "runtime_server_started": False,
            "preview_server_started": False,
            "external_deployment_performed": False,
            "repair_applied": False,
            "restore_executed": False,
        }

    workspace_root = _safe_workspace_root(generated_file.workspace_id)
    guard_result = validate_generated_file_write_path(
        workspace_root,
        generated_file.path,
    )

    if not guard_result.get("allowed"):
        return {
            "success": True,
            "found": True,
            "generated_file_id": generated_file.generated_file_id,
            "workflow_run_id": generated_file.workflow_run_id,
            "workspace_id": generated_file.workspace_id,
            "project_id": generated_file.project_id,
            "selected_path": generated_file.path,
            "write_status": "blocked",
            "block_reason": guard_result.get("reason"),
            "safety_mode": "approval_gated_static_preview_materialization",
            "sandbox_write_enabled": False,
            "approval_found": True,
            "approval_record": approval_result.get("approval_record"),
            "workspace_root": workspace_root,
            "path_guard": guard_result,
            "target_path": guard_result.get("resolved_target_path"),
            "filesystem_write_performed": False,
            "disk_write_performed": False,
            "generated_files_written_to_disk": False,
            "generated_code_execution_performed": False,
            "runtime_server_started": False,
            "preview_server_started": False,
            "external_deployment_performed": False,
            "repair_applied": False,
            "restore_executed": False,
        }

    target_path = Path(guard_result["resolved_target_path"])
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(generated_file.content_preview or "", encoding="utf-8")

    return {
        "success": True,
        "found": True,
        "generated_file_id": generated_file.generated_file_id,
        "workflow_run_id": generated_file.workflow_run_id,
        "workspace_id": generated_file.workspace_id,
        "project_id": generated_file.project_id,
        "selected_path": generated_file.path,
        "write_status": "written_to_local_sandbox",
        "block_reason": None,
        "safety_mode": "approval_gated_static_preview_materialization",
        "sandbox_write_enabled": True,
        "approval_found": True,
        "approval_record": approval_result.get("approval_record"),
        "workspace_root": workspace_root,
        "path_guard": guard_result,
        "target_path": str(target_path),
        "normalized_relative_path": guard_result.get("normalized_relative_path"),
        "content_hash": generated_file.content_hash,
        "bytes_written": len((generated_file.content_preview or "").encode("utf-8")),
        "filesystem_write_performed": True,
        "disk_write_performed": True,
        "generated_files_written_to_disk": True,
        "generated_code_execution_performed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "external_deployment_performed": False,
        "repair_applied": False,
        "restore_executed": False,
        "message": (
            "Generated file was written to the approved local sandbox only. "
            "No generated code was executed and no servers were started."
        ),
    }
