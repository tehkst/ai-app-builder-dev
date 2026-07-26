from __future__ import annotations

from typing import Any, Dict, List
from uuid import uuid4

from sqlalchemy.orm import Session

from app.platform.persistence.model_definitions.base import utc_now
from app.platform.persistence.models import PlatformGeneratedFile, PlatformGeneratedFileVersion
from app.platform.services.scoping_persistence_service import get_scoping_record


def rollback_generated_files_to_scoping_version(
    db: Session,
    *,
    scoping_request_id: str,
    restored_by: str = "platform_admin",
) -> Dict[str, Any]:
    """Restore every generated file tied to a prior SOW version's build.

    Each SOW version's build persists its own PlatformGeneratedFileVersion rows
    (keyed by workflow_run_id). Rolling back finds those rows for the target
    version and copies their content back onto the live PlatformGeneratedFile
    record, recording a new version snapshot so the rollback itself is also
    versioned and auditable.
    """

    target = get_scoping_record(db, scoping_request_id)
    if target is None:
        return {"success": False, "status": "scoping_request_not_found"}
    if not target.workflow_run_id:
        return {
            "success": False,
            "status": "no_build_linked_to_scoping_version",
            "scoping_request_id": scoping_request_id,
        }

    target_workflow_run_id = target.workflow_run_id
    generated_files = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.workflow_run_id == target_workflow_run_id)
        .all()
    )

    restored_paths: List[str] = []
    skipped_paths: List[str] = []

    for generated_file in generated_files:
        target_version = (
            db.query(PlatformGeneratedFileVersion)
            .filter(
                PlatformGeneratedFileVersion.generated_file_id == generated_file.generated_file_id,
                PlatformGeneratedFileVersion.workflow_run_id == target_workflow_run_id,
            )
            .order_by(PlatformGeneratedFileVersion.id.desc())
            .first()
        )
        if target_version is None:
            skipped_paths.append(generated_file.path)
            continue

        previous_content_hash = generated_file.content_hash
        generated_file.content_preview = target_version.content_preview
        generated_file.content_hash = target_version.content_hash
        generated_file.rollback_status = "restored"
        generated_file.updated_at = utc_now()

        db.add(
            PlatformGeneratedFileVersion(
                generated_file_version_id=f"generated_file_version_{uuid4().hex}",
                generated_file_id=generated_file.generated_file_id,
                workflow_run_id=target_workflow_run_id,
                workspace_id=generated_file.workspace_id,
                project_id=generated_file.project_id,
                previous_content_hash=previous_content_hash,
                content_hash=target_version.content_hash,
                content_preview=target_version.content_preview,
                path=generated_file.path,
                language=generated_file.language,
                purpose=generated_file.purpose,
                source_step_id=generated_file.source_step_id,
                source_agent_id=generated_file.source_agent_id,
                snapshot_status="restored",
                restore_status="restored_from_scoping_version",
                metadata_json=(
                    '{"restored_by": "%s", "restored_from_scoping_request_id": "%s"}'
                    % (restored_by, scoping_request_id)
                ),
            )
        )
        restored_paths.append(generated_file.path)

    db.commit()

    return {
        "success": bool(restored_paths),
        "status": "restored" if restored_paths else "nothing_to_restore",
        "scoping_request_id": scoping_request_id,
        "workflow_run_id": target_workflow_run_id,
        "restored_paths": restored_paths,
        "skipped_paths": skipped_paths,
        "write_mode": "db_preview_only",
        "filesystem_write_performed": False,
    }
