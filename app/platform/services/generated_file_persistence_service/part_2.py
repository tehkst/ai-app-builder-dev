# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import hashlib
import json
from typing import Any, Dict, List, Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from app.platform.persistence.models import PlatformGeneratedFile, utc_now
from app.platform.services.generated_file_rollback_service import (
    extract_generated_files_from_workflow_detail,
)

def list_persisted_generated_files(
    db: Session,
    workflow_run_id: str,
) -> Dict[str, Any]:
    records = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.workflow_run_id == workflow_run_id)
        .order_by(PlatformGeneratedFile.id.asc())
        .all()
    )

    files = [
        {
            "generated_file_id": record.generated_file_id,
            "workflow_run_id": record.workflow_run_id,
            "workspace_id": record.workspace_id,
            "project_id": record.project_id,
            "path": record.path,
            "language": record.language,
            "purpose": record.purpose,
            "content_preview": record.content_preview,
            "content_hash": record.content_hash,
            "write_status": record.write_status,
            "rollback_status": record.rollback_status,
            "source_step_id": record.source_step_id,
            "source_agent_id": record.source_agent_id,
        }
        for record in records
    ]

    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "persisted_file_count": len(files),
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "generated_files": files,
    }

def get_persisted_generated_file(
    db: Session,
    generated_file_id: str,
) -> Dict[str, Any]:
    record = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.generated_file_id == generated_file_id)
        .first()
    )

    if not record:
        return {
            "success": True,
            "found": False,
            "generated_file_id": generated_file_id,
            "write_mode": "db_preview_only",
            "disk_write_performed": False,
            "generated_file": None,
        }

    return {
        "success": True,
        "found": True,
        "generated_file_id": generated_file_id,
        "workflow_run_id": record.workflow_run_id,
        "workspace_id": record.workspace_id,
        "project_id": record.project_id,
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "generated_file": {
            "generated_file_id": record.generated_file_id,
            "workflow_run_id": record.workflow_run_id,
            "workspace_id": record.workspace_id,
            "project_id": record.project_id,
            "path": record.path,
            "language": record.language,
            "purpose": record.purpose,
            "content_preview": record.content_preview,
            "content_hash": record.content_hash,
            "write_status": record.write_status,
            "rollback_status": record.rollback_status,
            "source_step_id": record.source_step_id,
            "source_agent_id": record.source_agent_id,
        },
    }
