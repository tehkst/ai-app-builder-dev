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

def update_persisted_generated_file_content(
    db: Session,
    generated_file_id: str,
    content_preview: str,
    *,
    editor_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update persisted generated-file content in DB preview only.

    This editor intentionally does not write files to disk and does not execute
    generated code. It only mutates the DB-backed preview content.
    """

    record = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.generated_file_id == generated_file_id)
        .first()
    )

    if not record:
        return {
            "success": True,
            "found": False,
            "updated": False,
            "generated_file_id": generated_file_id,
            "write_mode": "db_preview_only",
            "write_status": "not_found",
            "disk_write_performed": False,
            "generated_code_execution_performed": False,
            "generated_file": None,
        }

    safe_content = "" if content_preview is None else str(content_preview)
    previous_content_hash = record.content_hash
    new_content_hash = _sha256_text(safe_content)

    record.content_preview = safe_content
    record.content_hash = new_content_hash
    record.write_status = "persisted_preview"
    record.metadata_json = json.dumps(
        {
            "persistence_mode": "db_preview_only",
            "editor_mode": "browser_workspace_file_editor",
            "editor_id": editor_id or "platform_admin",
            "previous_content_hash": previous_content_hash,
            "new_content_hash": new_content_hash,
            "content_changed": previous_content_hash != new_content_hash,
            "disk_write_performed": False,
            "generated_code_execution_performed": False,
        },
        sort_keys=True,
    )
    record.updated_at = utc_now()

    db.commit()
    db.refresh(record)

    return {
        "success": True,
        "found": True,
        "updated": True,
        "generated_file_id": record.generated_file_id,
        "workflow_run_id": record.workflow_run_id,
        "workspace_id": record.workspace_id,
        "project_id": record.project_id,
        "write_mode": "db_preview_only",
        "write_status": record.write_status,
        "previous_content_hash": previous_content_hash,
        "content_hash": record.content_hash,
        "content_changed": previous_content_hash != record.content_hash,
        "disk_write_performed": False,
        "generated_code_execution_performed": False,
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
