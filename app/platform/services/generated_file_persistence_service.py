from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformGeneratedFile, PlatformGeneratedFileVersion, utc_now
from app.platform.services.generated_file_rollback_service import extract_generated_files_from_workflow_detail

DEFAULT_WORKSPACE_ID = "platform-admin"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json_dump(value: Any, fallback: Any) -> str:
    if value is None:
        value = fallback
    return json.dumps(value, sort_keys=True)


def _json_load(value: Optional[str], fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _generated_file_id(workflow_run_id: str, path: str) -> str:
    digest = _sha256_text(f"{workflow_run_id}:{path}")[:24]
    return f"generated_file_{digest}"


def persist_generated_files_for_workflow(
    db: Session,
    workflow_detail: Dict[str, Any],
) -> Dict[str, Any]:
    """Persist generated files as DB-preview records only.

    This function is deliberately non-materializing: it never writes generated app files
    to disk, never executes generated code, and never deploys externally.
    """

    workflow_run_id = str(workflow_detail.get("workflow_run_id") or "").strip()
    if not workflow_run_id or not workflow_detail.get("found", True):
        return {
            "success": False,
            "persisted": False,
            "workflow_run_id": workflow_run_id or None,
            "generated_file_count": 0,
            "write_mode": "db_preview_only",
            "reason": "workflow_not_found_or_missing_id",
            "disk_write_performed": False,
            "filesystem_write_performed": False,
            "generated_code_execution_performed": False,
            "external_deployment_performed": False,
        }

    generated_files = extract_generated_files_from_workflow_detail(workflow_detail)
    persisted_count = 0
    version_count = 0
    persisted_paths: List[str] = []

    for file_entry in generated_files:
        path = str(file_entry.get("path") or "").strip()
        if not path:
            continue
        content_preview = str(file_entry.get("content_preview") or file_entry.get("content") or "")
        content_hash = _sha256_text(content_preview)
        generated_file_id = _generated_file_id(workflow_run_id, path)

        existing = (
            db.query(PlatformGeneratedFile)
            .filter(PlatformGeneratedFile.generated_file_id == generated_file_id)
            .first()
        )
        previous_content_hash = existing.content_hash if existing else None
        now = utc_now()

        if not existing:
            existing = PlatformGeneratedFile(
                generated_file_id=generated_file_id,
                workflow_run_id=workflow_run_id,
                workspace_id=str(file_entry.get("workspace_id") or DEFAULT_WORKSPACE_ID),
                project_id=file_entry.get("project_id"),
                path=path,
                content_hash=content_hash,
            )
            db.add(existing)

        existing.workflow_run_id = workflow_run_id
        existing.workspace_id = str(file_entry.get("workspace_id") or existing.workspace_id or DEFAULT_WORKSPACE_ID)
        existing.project_id = file_entry.get("project_id")
        existing.source_step_id = file_entry.get("source_step_id")
        existing.source_agent_id = file_entry.get("source_agent_id")
        existing.path = path
        existing.language = file_entry.get("language")
        existing.purpose = file_entry.get("purpose")
        existing.content_preview = content_preview
        existing.content_hash = content_hash
        existing.write_status = "persisted_preview"
        existing.rollback_status = "not_required"
        existing.metadata_json = _json_dump(
            {
                "write_mode": "db_preview_only",
                "original_write_status": file_entry.get("write_status"),
                "generated_code_execution_performed": False,
                "filesystem_write_performed": False,
                "external_deployment_performed": False,
            },
            {},
        )
        existing.updated_at = now
        persisted_count += 1
        persisted_paths.append(path)

        version = PlatformGeneratedFileVersion(
            generated_file_version_id=f"generated_file_version_{uuid.uuid4().hex}",
            generated_file_id=generated_file_id,
            workflow_run_id=workflow_run_id,
            workspace_id=existing.workspace_id,
            project_id=existing.project_id,
            previous_content_hash=previous_content_hash,
            content_hash=content_hash,
            content_preview=content_preview,
            path=path,
            language=existing.language,
            purpose=existing.purpose,
            source_step_id=existing.source_step_id,
            source_agent_id=existing.source_agent_id,
            snapshot_status="created",
            restore_status="not_restored",
            metadata_json=_json_dump({"write_mode": "db_preview_only"}, {}),
        )
        db.add(version)
        version_count += 1

    db.commit()
    return {
        "success": True,
        "persisted": True,
        "workflow_run_id": workflow_run_id,
        "generated_file_count": persisted_count,
        "generated_file_version_count": version_count,
        "persisted_paths": persisted_paths,
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "filesystem_write_performed": False,
        "generated_code_execution_performed": False,
        "external_deployment_performed": False,
        "materialization_performed": False,
    }


def list_persisted_generated_files(
    db: Session,
    *,
    workflow_run_id: str,
) -> Dict[str, Any]:
    rows = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.workflow_run_id == workflow_run_id)
        .order_by(PlatformGeneratedFile.created_at.asc())
        .all()
    )
    files = [
        {
            "generated_file_id": row.generated_file_id,
            "workflow_run_id": row.workflow_run_id,
            "path": row.path,
            "language": row.language,
            "purpose": row.purpose,
            "content_preview": row.content_preview,
            "content_hash": row.content_hash,
            "write_status": row.write_status,
            "rollback_status": row.rollback_status,
            "source_step_id": row.source_step_id,
            "source_agent_id": row.source_agent_id,
            "metadata": _json_load(row.metadata_json, {}),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "generated_file_count": len(files),
        "generated_files": files,
        "write_mode": "db_preview_only",
        "filesystem_write_performed": False,
        "generated_code_execution_performed": False,
        "external_deployment_performed": False,
    }
