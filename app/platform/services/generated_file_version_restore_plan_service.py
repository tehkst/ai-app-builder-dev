from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from app.platform.persistence.models import (
    PlatformGeneratedFile,
    PlatformGeneratedFileVersion,
)


def _file_summary(file_record: PlatformGeneratedFile) -> Dict[str, Any]:
    return {
        "generated_file_id": file_record.generated_file_id,
        "workflow_run_id": file_record.workflow_run_id,
        "workspace_id": file_record.workspace_id,
        "project_id": file_record.project_id,
        "path": file_record.path,
        "language": file_record.language,
        "content_hash": file_record.content_hash,
        "write_status": file_record.write_status,
        "rollback_status": file_record.rollback_status,
    }


def _version_summary(version: PlatformGeneratedFileVersion) -> Dict[str, Any]:
    return {
        "generated_file_version_id": version.generated_file_version_id,
        "generated_file_id": version.generated_file_id,
        "workflow_run_id": version.workflow_run_id,
        "workspace_id": version.workspace_id,
        "project_id": version.project_id,
        "version_number": version.version_number,
        "path": version.path,
        "language": version.language,
        "content_hash": version.content_hash,
        "previous_content_hash": version.previous_content_hash,
        "snapshot_status": version.snapshot_status,
        "restore_status": version.restore_status,
    }


def create_generated_file_version_restore_plan(
    db: Session,
    target_version_id: str,
) -> Dict[str, Any]:
    target_version = (
        db.query(PlatformGeneratedFileVersion)
        .filter(
            PlatformGeneratedFileVersion.generated_file_version_id
            == target_version_id
        )
        .first()
    )

    if not target_version:
        return {
            "success": True,
            "found": False,
            "target_version_id": target_version_id,
            "restore_mode": "plan_only",
            "write_mode": "db_preview_only",
            "disk_write_performed": False,
            "db_mutation_performed": False,
            "restore_plan": None,
        }

    current_file = (
        db.query(PlatformGeneratedFile)
        .filter(
            PlatformGeneratedFile.generated_file_id
            == target_version.generated_file_id
        )
        .first()
    )

    if not current_file:
        return {
            "success": True,
            "found": False,
            "target_version_found": True,
            "current_file_found": False,
            "target_version_id": target_version_id,
            "generated_file_id": target_version.generated_file_id,
            "restore_mode": "plan_only",
            "write_mode": "db_preview_only",
            "disk_write_performed": False,
            "db_mutation_performed": False,
            "restore_plan": None,
        }

    hash_changed = current_file.content_hash != target_version.content_hash
    path_changed = current_file.path != target_version.path
    language_changed = current_file.language != target_version.language
    content_preview_changed = (
        (current_file.content_preview or "")
        != (target_version.content_preview or "")
    )

    planned_action = (
        "replace_db_preview_content"
        if hash_changed or content_preview_changed
        else "no_op_already_matches_target_version"
    )

    manual_approval_required = planned_action != "no_op_already_matches_target_version"

    return {
        "success": True,
        "found": True,
        "target_version_id": target_version_id,
        "generated_file_id": target_version.generated_file_id,
        "restore_mode": "plan_only",
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "db_mutation_performed": False,
        "restore_plan": {
            "restore_type": "generated_file_version_restore",
            "restore_mode": "plan_only",
            "planned_action": planned_action,
            "safe_to_plan": True,
            "manual_approval_required": manual_approval_required,
            "execution_supported": False,
            "current_file": _file_summary(current_file),
            "target_version": _version_summary(target_version),
            "impact": {
                "hash_changed": hash_changed,
                "path_changed": path_changed,
                "language_changed": language_changed,
                "content_preview_changed": content_preview_changed,
                "current_content_hash": current_file.content_hash,
                "target_content_hash": target_version.content_hash,
                "current_write_status": current_file.write_status,
                "target_restore_status": target_version.restore_status,
            },
            "steps": [
                {
                    "step": 1,
                    "action": planned_action,
                    "description": (
                        "Plan to replace the DB preview content and hash with the selected version snapshot."
                        if planned_action == "replace_db_preview_content"
                        else "No restore action needed because the current file already matches the selected version."
                    ),
                    "execution_status": "not_executed",
                    "requires_manual_approval": manual_approval_required,
                }
            ],
        },
    }
