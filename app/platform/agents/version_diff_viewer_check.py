from __future__ import annotations

import json
from typing import Any, Dict

from fastapi.testclient import TestClient

from app.main import app
from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformGeneratedFile, utc_now
from app.platform.services.generated_file_persistence_service import (
    persist_generated_files_for_workflow,
)
from app.platform.services.generated_file_version_service import (
    create_generated_file_version_snapshot,
)
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail


def run_version_diff_viewer_check() -> Dict[str, Any]:
    create_platform_tables()

    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)

    checks = []

    dashboard_response = client.get("/platform/app-build/dashboard")
    dashboard_text = dashboard_response.text

    dashboard_passed = (
        dashboard_response.status_code == 200
        and "Version Diff Viewer" in dashboard_text
        and "workspaceVersionDiffPreview" in dashboard_text
        and "/diff/" in dashboard_text
    )
    checks.append(
        {
            "name": "dashboard_version_diff_viewer_html",
            "passed": dashboard_passed,
            "status_code": dashboard_response.status_code,
        }
    )

    run_response = client.post(
        "/platform/app-build/run",
        json={
            "app_request": "Build me a simple inventory app",
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
    first_generated_file_id = None
    first_version_id = None
    second_version_id = None

    if workflow_run_id:
        db = PlatformSessionLocal()
        try:
            detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
            persist_result = persist_generated_files_for_workflow(
                db,
                detail,
                workspace_id=f"workspace_{workflow_run_id}",
                project_id="project_version_diff_check",
            )

            generated_files = persist_result.get("generated_files") or []
            first_generated_file_id = (
                generated_files[0].get("generated_file_id")
                if generated_files
                else None
            )

            if first_generated_file_id:
                first_snapshot = create_generated_file_version_snapshot(
                    db,
                    first_generated_file_id,
                )
                first_version_id = first_snapshot.get("generated_file_version_id")

                file_record = (
                    db.query(PlatformGeneratedFile)
                    .filter(
                        PlatformGeneratedFile.generated_file_id
                        == first_generated_file_id
                    )
                    .first()
                )
                if file_record:
                    file_record.content_preview = (
                        (file_record.content_preview or "")
                        + "\\nAdd inventory item quantity tracking."
                    )
                    file_record.content_hash = (
                        "changed_for_version_diff_check_" + first_generated_file_id[-8:]
                    )
                    file_record.updated_at = utc_now()
                    db.commit()

                second_snapshot = create_generated_file_version_snapshot(
                    db,
                    first_generated_file_id,
                )
                second_version_id = second_snapshot.get("generated_file_version_id")
        finally:
            db.close()

    snapshots_passed = (
        persist_result.get("success") is True
        and persist_result.get("persisted_file_count", 0) >= 1
        and bool(first_generated_file_id)
        and bool(first_version_id)
        and bool(second_version_id)
        and first_version_id != second_version_id
        and persist_result.get("disk_write_performed") is False
    )
    checks.append(
        {
            "name": "two_version_snapshots_created",
            "passed": snapshots_passed,
            "first_generated_file_id": first_generated_file_id,
            "first_version_id": first_version_id,
            "second_version_id": second_version_id,
            "disk_write_performed": persist_result.get("disk_write_performed"),
        }
    )

    diff_response = client.get(
        f"/platform/app-build/generated-file-versions/{first_version_id}/diff/{second_version_id}"
    ) if first_version_id and second_version_id else None
    diff_data = diff_response.json() if diff_response is not None else {}
    diff = diff_data.get("diff") or {}

    diff_passed = (
        diff_response is not None
        and diff_response.status_code == 200
        and diff_data.get("success") is True
        and diff_data.get("found") is True
        and diff_data.get("write_mode") == "db_preview_only"
        and diff_data.get("disk_write_performed") is False
        and diff.get("same_generated_file") is not False
        and diff.get("hash_changed") is True
        and diff.get("content_changed") is True
        and diff.get("added_line_count", 0) >= 1
    )
    checks.append(
        {
            "name": "version_diff_api",
            "passed": diff_passed,
            "status_code": diff_response.status_code if diff_response is not None else None,
            "hash_changed": diff.get("hash_changed"),
            "added_line_count": diff.get("added_line_count"),
            "removed_line_count": diff.get("removed_line_count"),
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
        "second_version_id": second_version_id,
    }


def main() -> None:
    result = run_version_diff_viewer_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
