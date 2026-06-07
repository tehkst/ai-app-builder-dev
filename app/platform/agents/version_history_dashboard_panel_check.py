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


def run_version_history_dashboard_panel_check() -> Dict[str, Any]:
    create_platform_tables()

    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)

    checks = []

    dashboard_response = client.get("/platform/app-build/dashboard")
    dashboard_text = dashboard_response.text

    dashboard_passed = (
        dashboard_response.status_code == 200
        and "Version History" in dashboard_text
        and "Create Version Snapshot" in dashboard_text
        and "Load Version History" in dashboard_text
        and "workspaceVersionList" in dashboard_text
        and "workspaceVersionPreview" in dashboard_text
        and "/generated-file-versions/" in dashboard_text
        and "/versions" in dashboard_text
    )
    checks.append(
        {
            "name": "dashboard_version_history_panel_html",
            "passed": dashboard_passed,
            "status_code": dashboard_response.status_code,
        }
    )

    run_response = client.post(
        "/platform/app-build/run",
        json={
            "app_request": "Build me a simple CRM app",
            "real_bridge": True,
        },
    )
    run_data = run_response.json()
    workflow_run_id = (run_data.get("summary") or {}).get("workflow_run_id")

    run_passed = (
        run_response.status_code == 200
        and run_data.get("success") is True
        and run_data.get("status") == "completed"
        and bool(workflow_run_id)
    )
    checks.append(
        {
            "name": "workflow_run_created",
            "passed": run_passed,
            "status_code": run_response.status_code,
            "workflow_run_id": workflow_run_id,
        }
    )

    persist_result: Dict[str, Any] = {}
    if workflow_run_id:
        db = PlatformSessionLocal()
        try:
            detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
            persist_result = persist_generated_files_for_workflow(
                db,
                detail,
                workspace_id=f"workspace_{workflow_run_id}",
                project_id="project_version_dashboard_check",
            )
        finally:
            db.close()

    persist_passed = (
        persist_result.get("success") is True
        and persist_result.get("persisted_file_count", 0) >= 1
        and persist_result.get("disk_write_performed") is False
    )
    checks.append(
        {
            "name": "generated_files_persisted",
            "passed": persist_passed,
            "persisted_file_count": persist_result.get("persisted_file_count", 0),
            "disk_write_performed": persist_result.get("disk_write_performed"),
        }
    )

    files_response = client.get(
        f"/platform/app-build/runs/{workflow_run_id}/persisted-files"
    ) if workflow_run_id else None
    files_data = files_response.json() if files_response is not None else {}
    files = files_data.get("generated_files") or []
    first_generated_file_id = files[0].get("generated_file_id") if files else None

    files_passed = (
        files_response is not None
        and files_response.status_code == 200
        and files_data.get("success") is True
        and files_data.get("persisted_file_count", 0) >= 1
        and bool(first_generated_file_id)
    )
    checks.append(
        {
            "name": "persisted_files_available_for_panel",
            "passed": files_passed,
            "status_code": files_response.status_code if files_response is not None else None,
            "first_generated_file_id": first_generated_file_id,
        }
    )

    create_version_response = client.post(
        f"/platform/app-build/generated-files/{first_generated_file_id}/versions"
    ) if first_generated_file_id else None
    create_version_data = (
        create_version_response.json() if create_version_response is not None else {}
    )
    first_version_id = create_version_data.get("generated_file_version_id")

    create_version_passed = (
        create_version_response is not None
        and create_version_response.status_code == 200
        and create_version_data.get("success") is True
        and create_version_data.get("snapshot_created") is True
        and create_version_data.get("write_mode") == "db_preview_only"
        and create_version_data.get("disk_write_performed") is False
        and bool(first_version_id)
    )
    checks.append(
        {
            "name": "single_file_version_snapshot_created",
            "passed": create_version_passed,
            "status_code": create_version_response.status_code if create_version_response is not None else None,
            "first_version_id": first_version_id,
        }
    )

    versions_response = client.get(
        f"/platform/app-build/generated-files/{first_generated_file_id}/versions"
    ) if first_generated_file_id else None
    versions_data = versions_response.json() if versions_response is not None else {}

    versions_passed = (
        versions_response is not None
        and versions_response.status_code == 200
        and versions_data.get("success") is True
        and versions_data.get("version_count", 0) >= 1
        and versions_data.get("disk_write_performed") is False
    )
    checks.append(
        {
            "name": "version_history_available_for_panel",
            "passed": versions_passed,
            "status_code": versions_response.status_code if versions_response is not None else None,
            "version_count": versions_data.get("version_count", 0),
        }
    )

    version_response = client.get(
        f"/platform/app-build/generated-file-versions/{first_version_id}"
    ) if first_version_id else None
    version_data = version_response.json() if version_response is not None else {}
    version = version_data.get("generated_file_version") or {}

    version_passed = (
        version_response is not None
        and version_response.status_code == 200
        and version_data.get("success") is True
        and version_data.get("found") is True
        and version.get("restore_status") == "not_restored"
        and bool(version.get("content_preview"))
        and bool(version.get("content_hash"))
    )
    checks.append(
        {
            "name": "version_detail_available_for_panel",
            "passed": version_passed,
            "status_code": version_response.status_code if version_response is not None else None,
            "restore_status": version.get("restore_status"),
        }
    )

    passed = all(check["passed"] for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "checks": checks,
        "workflow_run_id": workflow_run_id,
        "first_generated_file_id": first_generated_file_id,
        "first_version_id": first_version_id,
    }


def main() -> None:
    result = run_version_history_dashboard_panel_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
