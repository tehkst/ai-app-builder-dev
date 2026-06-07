from __future__ import annotations

import json
from typing import Any, Dict

from fastapi.testclient import TestClient

from app.main import app
from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.generated_file_persistence_service import (
    list_persisted_generated_files,
    persist_generated_files_for_workflow,
)
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail


def run_generated_file_persistence_check() -> Dict[str, Any]:
    create_platform_tables()

    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)

    checks = []

    run_response = client.post(
        "/platform/app-build/run",
        json={
            "app_request": "Build me a simple CRM app with contacts and notes",
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
    list_result: Dict[str, Any] = {}

    if workflow_run_id:
        db = PlatformSessionLocal()
        try:
            detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
            persist_result = persist_generated_files_for_workflow(
                db,
                detail,
                workspace_id=f"workspace_{workflow_run_id}",
                project_id="project_persistence_check",
            )
            list_result = list_persisted_generated_files(
                db,
                workflow_run_id=workflow_run_id,
            )
        finally:
            db.close()

    persisted_files = list_result.get("generated_files") or []
    first_file = persisted_files[0] if persisted_files else {}

    persist_passed = (
        persist_result.get("success") is True
        and persist_result.get("persisted") is True
        and persist_result.get("generated_file_count") >= 1
        and persist_result.get("persisted_file_count") == persist_result.get("generated_file_count")
        and persist_result.get("write_mode") == "db_preview_only"
        and persist_result.get("disk_write_performed") is False
    )
    checks.append(
        {
            "name": "generated_files_persisted",
            "passed": persist_passed,
            "persisted_file_count": persist_result.get("persisted_file_count", 0),
            "write_mode": persist_result.get("write_mode"),
            "disk_write_performed": persist_result.get("disk_write_performed"),
        }
    )

    list_passed = (
        list_result.get("success") is True
        and list_result.get("persisted_file_count") == persist_result.get("persisted_file_count")
        and list_result.get("disk_write_performed") is False
        and first_file.get("write_status") == "persisted_preview"
        and bool(first_file.get("content_hash"))
        and bool(first_file.get("workspace_id"))
    )
    checks.append(
        {
            "name": "persisted_files_listed",
            "passed": list_passed,
            "persisted_file_count": list_result.get("persisted_file_count", 0),
            "first_file": first_file,
        }
    )

    passed = all(check["passed"] for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "checks": checks,
        "workflow_run_id": workflow_run_id,
        "persist_result": persist_result,
    }


def main() -> None:
    result = run_generated_file_persistence_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
