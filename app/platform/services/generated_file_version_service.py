from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.platform.persistence.models import (
    PlatformGeneratedFile,
    PlatformGeneratedFileVersion,
)


def _version_to_dict(record: PlatformGeneratedFileVersion) -> Dict[str, Any]:
    return {
        "generated_file_version_id": record.generated_file_version_id,
        "generated_file_id": record.generated_file_id,
        "workflow_run_id": record.workflow_run_id,
        "workspace_id": record.workspace_id,
        "project_id": record.project_id,
        "version_number": record.version_number,
        "previous_content_hash": record.previous_content_hash,
        "content_hash": record.content_hash,
        "content_preview": record.content_preview,
        "path": record.path,
        "language": record.language,
        "purpose": record.purpose,
        "source_step_id": record.source_step_id,
        "source_agent_id": record.source_agent_id,
        "snapshot_status": record.snapshot_status,
        "restore_status": record.restore_status,
    }


def create_generated_file_version_snapshot(
    db: Session,
    generated_file_id: str,
    *,
    snapshot_status: str = "created",
    restore_status: str = "not_restored",
    metadata: Optional[Dict[str, Any]] = None,
    commit: bool = True,
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
            "generated_file_id": generated_file_id,
            "snapshot_created": False,
            "write_mode": "db_preview_only",
            "disk_write_performed": False,
            "generated_file_version": None,
        }

    latest_version = (
        db.query(PlatformGeneratedFileVersion)
        .filter(PlatformGeneratedFileVersion.generated_file_id == generated_file_id)
        .order_by(PlatformGeneratedFileVersion.version_number.desc())
        .first()
    )

    previous_content_hash = latest_version.content_hash if latest_version else None
    next_version_number = (latest_version.version_number + 1) if latest_version else 1

    version = PlatformGeneratedFileVersion(
        generated_file_version_id=f"generated_file_version_{uuid4().hex}",
        generated_file_id=generated_file.generated_file_id,
        workflow_run_id=generated_file.workflow_run_id,
        workspace_id=generated_file.workspace_id,
        project_id=generated_file.project_id,
        version_number=next_version_number,
        previous_content_hash=previous_content_hash,
        content_hash=generated_file.content_hash,
        content_preview=generated_file.content_preview,
        path=generated_file.path,
        language=generated_file.language,
        purpose=generated_file.purpose,
        source_step_id=generated_file.source_step_id,
        source_agent_id=generated_file.source_agent_id,
        snapshot_status=snapshot_status,
        restore_status=restore_status,
        metadata_json=json.dumps(
            {
                "snapshot_mode": "db_preview_only",
                "disk_write_performed": False,
                "source_write_status": generated_file.write_status,
                "source_rollback_status": generated_file.rollback_status,
                **(metadata or {}),
            },
            sort_keys=True,
        ),
    )

    db.add(version)

    if commit:
        db.commit()
        db.refresh(version)
    else:
        db.flush()

    return {
        "success": True,
        "found": True,
        "snapshot_created": True,
        "generated_file_id": generated_file_id,
        "generated_file_version_id": version.generated_file_version_id,
        "version_number": version.version_number,
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "generated_file_version": _version_to_dict(version),
    }


def create_version_snapshots_for_workflow(
    db: Session,
    workflow_run_id: str,
) -> Dict[str, Any]:
    generated_files = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.workflow_run_id == workflow_run_id)
        .order_by(PlatformGeneratedFile.id.asc())
        .all()
    )

    versions: List[Dict[str, Any]] = []

    for generated_file in generated_files:
        result = create_generated_file_version_snapshot(
            db,
            generated_file.generated_file_id,
        )
        if result.get("snapshot_created"):
            versions.append(result["generated_file_version"])

    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "generated_file_count": len(generated_files),
        "version_count": len(versions),
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "generated_file_versions": versions,
    }


def list_generated_file_versions(
    db: Session,
    generated_file_id: str,
) -> Dict[str, Any]:
    versions = (
        db.query(PlatformGeneratedFileVersion)
        .filter(PlatformGeneratedFileVersion.generated_file_id == generated_file_id)
        .order_by(PlatformGeneratedFileVersion.version_number.asc())
        .all()
    )

    return {
        "success": True,
        "generated_file_id": generated_file_id,
        "version_count": len(versions),
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "generated_file_versions": [_version_to_dict(version) for version in versions],
    }


def get_generated_file_version(
    db: Session,
    generated_file_version_id: str,
) -> Dict[str, Any]:
    version = (
        db.query(PlatformGeneratedFileVersion)
        .filter(
            PlatformGeneratedFileVersion.generated_file_version_id
            == generated_file_version_id
        )
        .first()
    )

    if not version:
        return {
            "success": True,
            "found": False,
            "generated_file_version_id": generated_file_version_id,
            "write_mode": "db_preview_only",
            "disk_write_performed": False,
            "generated_file_version": None,
        }

    return {
        "success": True,
        "found": True,
        "generated_file_version_id": generated_file_version_id,
        "generated_file_id": version.generated_file_id,
        "workflow_run_id": version.workflow_run_id,
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "generated_file_version": _version_to_dict(version),
    }
