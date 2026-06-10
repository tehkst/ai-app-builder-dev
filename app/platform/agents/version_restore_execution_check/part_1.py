# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import json
from typing import Any, Dict, List
from fastapi.testclient import TestClient
from app.main import app
from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.generated_file_persistence_service import (
    persist_generated_files_for_workflow,
)
from app.platform.services.generated_file_version_service import (
    create_generated_file_version_snapshot,
)
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail

def _create_target_version(client: TestClient) -> Dict[str, Any]:
    run_response = client.post(
        "/platform/app-build/run",
        json={
            "app_request": "Build me a safe restore execution app",
            "real_bridge": True,
        },
    )
    run_data = run_response.json()
    workflow_run_id = (run_data.get("execution") or {}).get("workflow_run_id")

    persist_result: Dict[str, Any] = {}
    first_generated_file_id = None
    first_version_id = None
    target_content = None
    changed_content = None

    if workflow_run_id:
        db = PlatformSessionLocal()
        try:
            detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
            persist_result = persist_generated_files_for_workflow(
                db,
                detail,
                workspace_id=f"workspace_{workflow_run_id}",
                project_id="project_restore_execution_check",
            )

            generated_files = persist_result.get("generated_files") or []
            first_generated_file_id = (
                generated_files[0].get("generated_file_id")
                if generated_files
                else None
            )

            if first_generated_file_id:
                snapshot = create_generated_file_version_snapshot(
                    db,
                    first_generated_file_id,
                )
                first_version_id = snapshot.get("generated_file_version_id")
                target_content = (
                    snapshot.get("generated_file_version") or {}
                ).get("content_preview")

                file_record = (
                    db.query(PlatformGeneratedFile)
                    .filter(
                        PlatformGeneratedFile.generated_file_id
                        == first_generated_file_id
                    )
                    .first()
                )
                if file_record:
                    changed_content = (
                        (file_record.content_preview or "")
                        + "\\nCurrent DB preview changed before safe restore execution."
                    )
                    file_record.content_preview = changed_content
                    file_record.content_hash = (
                        "current_changed_for_safe_restore_execution_"
                        + first_generated_file_id[-8:]
                    )
                    db.commit()
        finally:
            db.close()

    return {
        "name": "target_version_snapshot_created",
        "passed": bool(workflow_run_id)
        and run_response.status_code == 200
        and bool(first_generated_file_id)
        and bool(first_version_id)
        and persist_result.get("disk_write_performed") is False
        and bool(target_content)
        and bool(changed_content)
        and target_content != changed_content,
        "status_code": run_response.status_code,
        "workflow_run_id": workflow_run_id,
        "first_generated_file_id": first_generated_file_id,
        "first_version_id": first_version_id,
        "target_content": target_content,
        "changed_content": changed_content,
        "disk_write_performed": persist_result.get("disk_write_performed"),
        "persisted_file_count": persist_result.get("persisted_file_count"),
    }

def _create_approval(client: TestClient, target_version_id: str) -> Dict[str, Any]:
    response = client.post(
        f"/platform/app-build/generated-file-versions/{target_version_id}/restore-approval-requests",
        json={},
    )
    data = response.json()

    return {
        "name": "approval_request_created",
        "passed": response.status_code == 200
        and data.get("approval_created") is True
        and bool(data.get("approval_id"))
        and data.get("restore_execution_performed") is False,
        "status_code": response.status_code,
        "approval_id": data.get("approval_id"),
        "restore_execution_performed": data.get("restore_execution_performed"),
    }
