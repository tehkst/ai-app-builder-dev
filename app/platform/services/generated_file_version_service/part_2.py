# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from app.platform.persistence.models import (
    PlatformGeneratedFile,
    PlatformGeneratedFileVersion,
)

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
