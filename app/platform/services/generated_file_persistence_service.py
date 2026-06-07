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


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_workspace_id(workflow_run_id: str) -> str:
    safe_run_id = str(workflow_run_id or "unknown").strip() or "unknown"
    return f"workspace_{safe_run_id}"


def persist_generated_files_for_workflow(
    db: Session,
    workflow_detail: Dict[str, Any],
    workspace_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    workflow_run_id = str(workflow_detail.get("workflow_run_id") or "").strip()
    if not workflow_run_id:
        return {
            "success": False,
            "persisted": False,
            "error": "workflow_run_id is required",
            "generated_file_count": 0,
            "persisted_file_count": 0,
            "generated_files": [],
        }

    resolved_workspace_id = workspace_id or _stable_workspace_id(workflow_run_id)
    generated_files = extract_generated_files_from_workflow_detail(workflow_detail)

    persisted_files: List[Dict[str, Any]] = []

    for file_entry in generated_files:
        path = str(file_entry.get("path") or "").strip()
        if not path:
            continue

        content_preview = str(file_entry.get("content_preview") or "")
        content_hash = _sha256_text(content_preview)

        existing = (
            db.query(PlatformGeneratedFile)
            .filter(
                PlatformGeneratedFile.workflow_run_id == workflow_run_id,
                PlatformGeneratedFile.path == path,
            )
            .first()
        )

        if existing:
            existing.workspace_id = resolved_workspace_id
            existing.project_id = project_id
            existing.source_step_id = file_entry.get("source_step_id")
            existing.source_agent_id = file_entry.get("source_agent_id")
            existing.language = file_entry.get("language")
            existing.purpose = file_entry.get("purpose")
            existing.content_preview = content_preview
            existing.content_hash = content_hash
            existing.write_status = "persisted_preview"
            existing.rollback_status = "not_required"
            existing.metadata_json = json.dumps(
                {
                    "original_write_status": file_entry.get("write_status"),
                    "persistence_mode": "db_preview_only",
                    "disk_write_performed": False,
                },
                sort_keys=True,
            )
            existing.updated_at = utc_now()
            record = existing
        else:
            record = PlatformGeneratedFile(
                generated_file_id=f"generated_file_{uuid4().hex}",
                workflow_run_id=workflow_run_id,
                workspace_id=resolved_workspace_id,
                project_id=project_id,
                source_step_id=file_entry.get("source_step_id"),
                source_agent_id=file_entry.get("source_agent_id"),
                path=path,
                language=file_entry.get("language"),
                purpose=file_entry.get("purpose"),
                content_preview=content_preview,
                content_hash=content_hash,
                write_status="persisted_preview",
                rollback_status="not_required",
                metadata_json=json.dumps(
                    {
                        "original_write_status": file_entry.get("write_status"),
                        "persistence_mode": "db_preview_only",
                        "disk_write_performed": False,
                    },
                    sort_keys=True,
                ),
            )
            db.add(record)

        persisted_files.append(
            {
                "generated_file_id": record.generated_file_id,
                "workflow_run_id": workflow_run_id,
                "workspace_id": resolved_workspace_id,
                "project_id": project_id,
                "path": path,
                "language": file_entry.get("language"),
                "purpose": file_entry.get("purpose"),
                "content_hash": content_hash,
                "write_status": "persisted_preview",
                "rollback_status": "not_required",
                "source_step_id": file_entry.get("source_step_id"),
                "source_agent_id": file_entry.get("source_agent_id"),
            }
        )

    db.commit()

    return {
        "success": True,
        "persisted": True,
        "workflow_run_id": workflow_run_id,
        "workspace_id": resolved_workspace_id,
        "project_id": project_id,
        "generated_file_count": len(generated_files),
        "persisted_file_count": len(persisted_files),
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "generated_files": persisted_files,
    }


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

