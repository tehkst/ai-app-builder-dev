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


def run_workspace_file_retrieval_api_check() -> Dict[str, Any]:
    create_platform_tables()

    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)

    checks = []

    run_response = client.post(
        "/platform/app-build/run",
        json={
            "app_request": "Build me a simple inventory app with products and stock levels",
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
                project_id="project_retrieval_check",
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

    list_data: Dict[str, Any] = {}
    list_status_code = None
    first_generated_file_id = None

    if workflow_run_id:
        list_response = client.get(
            f"/platform/app-build/runs/{workflow_run_id}/persisted-files"
        )
        list_status_code = list_response.status_code
        list_data = list_response.json()
        persisted_files = list_data.get("generated_files") or []
        if persisted_files:
            first_generated_file_id = persisted_files[0].get("generated_file_id")

    list_passed = (
        list_status_code == 200
        and list_data.get("success") is True
        and list_data.get("workflow_run_id") == workflow_run_id
        and list_data.get("persisted_file_count") == persist_result.get("persisted_file_count")
        and list_data.get("write_mode") == "db_preview_only"
        and list_data.get("disk_write_performed") is False
        and bool(first_generated_file_id)
    )
    checks.append(
        {
            "name": "persisted_files_list_api",
            "passed": list_passed,
            "status_code": list_status_code,
            "persisted_file_count": list_data.get("persisted_file_count", 0),
            "first_generated_file_id": first_generated_file_id,
        }
    )

    single_data: Dict[str, Any] = {}
    single_status_code = None

    if first_generated_file_id:
        single_response = client.get(
            f"/platform/app-build/generated-files/{first_generated_file_id}"
        )
        single_status_code = single_response.status_code
        single_data = single_response.json()

    generated_file = single_data.get("generated_file") or {}
    single_passed = (
        single_status_code == 200
        and single_data.get("success") is True
        and single_data.get("found") is True
        and single_data.get("generated_file_id") == first_generated_file_id
        and single_data.get("write_mode") == "db_preview_only"
        and single_data.get("disk_write_performed") is False
        and generated_file.get("write_status") == "persisted_preview"
        and bool(generated_file.get("content_hash"))
        and bool(generated_file.get("content_preview"))
    )
    checks.append(
        {
            "name": "single_persisted_file_api",
            "passed": single_passed,
            "status_code": single_status_code,
            "generated_file_id": first_generated_file_id,
            "path": generated_file.get("path"),
            "write_status": generated_file.get("write_status"),
        }
    )

    passed = all(check["passed"] for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "checks": checks,
        "workflow_run_id": workflow_run_id,
        "first_generated_file_id": first_generated_file_id,
    }


def main() -> None:
    result = run_workspace_file_retrieval_api_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
