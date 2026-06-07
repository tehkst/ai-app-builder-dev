from __future__ import annotations

import json
from typing import Any, Dict

from fastapi.testclient import TestClient

from app.main import app
from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.generated_file_persistence_service import (
    persist_generated_files_for_workflow,
)
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail


def run_check() -> Dict[str, Any]:
    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)

    run_payload = {
        "app_request": "Build a tiny test app for browser workspace file editor validation.",
        "workflow_name": "browser_workspace_file_editor_check",
        "real_bridge": True,
    }

    run_response = client.post("/platform/app-build/run", json=run_payload)
    run_data = run_response.json()
    workflow_run_id = (run_data.get("execution") or {}).get("workflow_run_id")

    create_platform_tables()

    persist_status_code = None
    persist_data: Dict[str, Any] = {}
    generated_file_id = None

    if workflow_run_id:
        db = PlatformSessionLocal()
        try:
            detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
            persist_data = persist_generated_files_for_workflow(
                db,
                detail,
                workspace_id=f"workspace_{workflow_run_id}",
                project_id="project_browser_workspace_file_editor_check",
            )
            persist_status_code = 200
            generated_files = persist_data.get("generated_files") or []
            first_file = generated_files[0] if generated_files else {}
            generated_file_id = first_file.get("generated_file_id")
        finally:
            db.close()

    before_response = client.get(
        f"/platform/app-build/generated-files/{generated_file_id}"
    )
    before_data = before_response.json()
    before_file = before_data.get("generated_file") or {}
    before_hash = before_file.get("content_hash")

    edited_content = (
        str(before_file.get("content_preview") or "")
        + "\\n# Browser workspace file editor validation edit."
    )

    update_response = client.put(
        f"/platform/app-build/generated-files/{generated_file_id}/content",
        json={
            "content_preview": edited_content,
            "editor_id": "browser_workspace_file_editor_check",
        },
    )
    update_data = update_response.json()
    version_snapshot = update_data.get("version_snapshot") or {}
    generated_file_version = update_data.get("generated_file_version") or {}

    after_response = client.get(
        f"/platform/app-build/generated-files/{generated_file_id}"
    )
    after_data = after_response.json()
    after_file = after_data.get("generated_file") or {}

    checks = [
        {
            "name": "workflow_created",
            "passed": run_response.status_code == 200 and bool(workflow_run_id),
            "status_code": run_response.status_code,
            "workflow_run_id": workflow_run_id,
        },
        {
            "name": "generated_files_persisted",
            "passed": persist_status_code == 200
            and bool(generated_file_id)
            and persist_data.get("write_mode") == "db_preview_only"
            and persist_data.get("disk_write_performed") is False,
            "status_code": persist_status_code,
            "generated_file_id": generated_file_id,
        },
        {
            "name": "editor_saved_db_preview_only",
            "passed": update_response.status_code == 200
            and update_data.get("updated") is True
            and update_data.get("write_mode") == "db_preview_only"
            and update_data.get("disk_write_performed") is False
            and update_data.get("generated_code_execution_performed") is False,
            "status_code": update_response.status_code,
            "previous_content_hash": update_data.get("previous_content_hash"),
            "content_hash": update_data.get("content_hash"),
        },
        {
            "name": "browser_editor_snapshot_created",
            "passed": update_data.get("snapshot_created") is True
            and generated_file_version.get("snapshot_status") == "browser_editor_snapshot"
            and generated_file_version.get("restore_status") == "not_restored",
            "snapshot_created": update_data.get("snapshot_created"),
            "snapshot_status": generated_file_version.get("snapshot_status"),
            "restore_status": generated_file_version.get("restore_status"),
            "version_number": generated_file_version.get("version_number"),
        },
        {
            "name": "edited_content_reloaded",
            "passed": after_response.status_code == 200
            and after_file.get("content_preview") == edited_content
            and after_file.get("content_hash") == update_data.get("content_hash")
            and before_hash != after_file.get("content_hash"),
            "status_code": after_response.status_code,
            "before_hash": before_hash,
            "after_hash": after_file.get("content_hash"),
        },
        {
            "name": "snapshot_safety_flags",
            "passed": version_snapshot.get("disk_write_performed") is False,
            "disk_write_performed": version_snapshot.get("disk_write_performed"),
        },
    ]

    return {
        "success": all(check["passed"] for check in checks),
        "passed": all(check["passed"] for check in checks),
        "workflow_run_id": workflow_run_id,
        "generated_file_id": generated_file_id,
        "checks": checks,
    }


if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
