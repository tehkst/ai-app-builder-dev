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


def run_generated_file_version_history_check() -> Dict[str, Any]:
    create_platform_tables()

    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)

    checks = []

    run_response = client.post(
        "/platform/app-build/run",
        json={
            "app_request": "Build me a simple notes app with tags",
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
                project_id="project_version_history_check",
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
            "name": "generated_files_persisted",
            "passed": persist_passed,
            "persisted_file_count": persist_result.get("persisted_file_count", 0),
            "write_mode": persist_result.get("write_mode"),
            "disk_write_performed": persist_result.get("disk_write_performed"),
        }
    )

    create_versions_response = client.post(
        f"/platform/app-build/runs/{workflow_run_id}/generated-file-versions"
    ) if workflow_run_id else None
    create_versions_data = (
        create_versions_response.json() if create_versions_response is not None else {}
    )
    versions = create_versions_data.get("generated_file_versions") or []
    first_version = versions[0] if versions else {}
    first_generated_file_id = first_version.get("generated_file_id")
    first_version_id = first_version.get("generated_file_version_id")

    create_versions_passed = (
        create_versions_response is not None
        and create_versions_response.status_code == 200
        and create_versions_data.get("success") is True
        and create_versions_data.get("version_count") == persist_result.get("persisted_file_count")
        and create_versions_data.get("write_mode") == "db_preview_only"
        and create_versions_data.get("disk_write_performed") is False
        and first_version.get("version_number") == 1
        and first_version.get("restore_status") == "not_restored"
        and bool(first_version_id)
    )
    checks.append(
        {
            "name": "workflow_version_snapshots_created",
            "passed": create_versions_passed,
            "status_code": create_versions_response.status_code if create_versions_response is not None else None,
            "version_count": create_versions_data.get("version_count", 0),
            "first_version_id": first_version_id,
        }
    )

    list_versions_response = client.get(
        f"/platform/app-build/generated-files/{first_generated_file_id}/versions"
    ) if first_generated_file_id else None
    list_versions_data = (
        list_versions_response.json() if list_versions_response is not None else {}
    )

    list_versions_passed = (
        list_versions_response is not None
        and list_versions_response.status_code == 200
        and list_versions_data.get("success") is True
        and list_versions_data.get("version_count", 0) >= 1
        and list_versions_data.get("write_mode") == "db_preview_only"
        and list_versions_data.get("disk_write_performed") is False
    )
    checks.append(
        {
            "name": "generated_file_versions_listed",
            "passed": list_versions_passed,
            "status_code": list_versions_response.status_code if list_versions_response is not None else None,
            "version_count": list_versions_data.get("version_count", 0),
        }
    )

    get_version_response = client.get(
        f"/platform/app-build/generated-file-versions/{first_version_id}"
    ) if first_version_id else None
    get_version_data = get_version_response.json() if get_version_response is not None else {}
    version_detail = get_version_data.get("generated_file_version") or {}

    get_version_passed = (
        get_version_response is not None
        and get_version_response.status_code == 200
        and get_version_data.get("success") is True
        and get_version_data.get("found") is True
        and get_version_data.get("write_mode") == "db_preview_only"
        and get_version_data.get("disk_write_performed") is False
        and version_detail.get("generated_file_version_id") == first_version_id
        and version_detail.get("snapshot_status") == "created"
        and version_detail.get("restore_status") == "not_restored"
        and bool(version_detail.get("content_hash"))
        and bool(version_detail.get("content_preview"))
    )
    checks.append(
        {
            "name": "generated_file_version_retrieved",
            "passed": get_version_passed,
            "status_code": get_version_response.status_code if get_version_response is not None else None,
            "version_id": first_version_id,
            "version_number": version_detail.get("version_number"),
            "restore_status": version_detail.get("restore_status"),
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
    result = run_generated_file_version_history_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
