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


def run_workspace_explorer_dashboard_check() -> Dict[str, Any]:
    create_platform_tables()

    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)

    checks = []

    dashboard_response = client.get("/platform/app-build/dashboard")
    dashboard_passed = (
        dashboard_response.status_code == 200
        and "Workspace Explorer" in dashboard_response.text
        and "workspaceFileList" in dashboard_response.text
        and "/persisted-files" in dashboard_response.text
        and "/platform/app-build/generated-files/" in dashboard_response.text
        and "Viewer-only: no disk writes, no execution" in dashboard_response.text
    )
    checks.append(
        {
            "name": "dashboard_workspace_explorer_html",
            "passed": dashboard_passed,
            "status_code": dashboard_response.status_code,
        }
    )

    run_response = client.post(
        "/platform/app-build/run",
        json={
            "app_request": "Build me a simple task tracker app",
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
                project_id="project_workspace_explorer_check",
            )
        finally:
            db.close()

    persist_passed = (
        persist_result.get("success") is True
        and persist_result.get("persisted_file_count", 0) >= 1
        and persist_result.get("write_mode") == "db_preview_only"
        and persist_result.get("disk_write_performed") is False
    )
    checks.append(
        {
            "name": "generated_files_persisted_for_explorer",
            "passed": persist_passed,
            "persisted_file_count": persist_result.get("persisted_file_count", 0),
            "write_mode": persist_result.get("write_mode"),
            "disk_write_performed": persist_result.get("disk_write_performed"),
        }
    )

    list_response = client.get(
        f"/platform/app-build/runs/{workflow_run_id}/persisted-files"
    ) if workflow_run_id else None
    list_data = list_response.json() if list_response is not None else {}
    files = list_data.get("generated_files") or []
    first_file_id = files[0].get("generated_file_id") if files else None

    list_passed = (
        list_response is not None
        and list_response.status_code == 200
        and list_data.get("success") is True
        and list_data.get("persisted_file_count") == persist_result.get("persisted_file_count")
        and list_data.get("disk_write_performed") is False
        and bool(first_file_id)
    )
    checks.append(
        {
            "name": "workspace_explorer_list_api",
            "passed": list_passed,
            "status_code": list_response.status_code if list_response is not None else None,
            "persisted_file_count": list_data.get("persisted_file_count", 0),
            "first_file_id": first_file_id,
        }
    )

    single_response = client.get(
        f"/platform/app-build/generated-files/{first_file_id}"
    ) if first_file_id else None
    single_data = single_response.json() if single_response is not None else {}
    selected_file = single_data.get("generated_file") or {}

    single_passed = (
        single_response is not None
        and single_response.status_code == 200
        and single_data.get("success") is True
        and single_data.get("found") is True
        and selected_file.get("write_status") == "persisted_preview"
        and bool(selected_file.get("content_hash"))
        and bool(selected_file.get("content_preview"))
    )
    checks.append(
        {
            "name": "workspace_explorer_single_file_api",
            "passed": single_passed,
            "status_code": single_response.status_code if single_response is not None else None,
            "path": selected_file.get("path"),
            "write_status": selected_file.get("write_status"),
        }
    )

    passed = all(check["passed"] for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "checks": checks,
        "workflow_run_id": workflow_run_id,
        "first_file_id": first_file_id,
    }


def main() -> None:
    result = run_workspace_explorer_dashboard_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
