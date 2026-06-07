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


def run_version_restore_planning_check() -> Dict[str, Any]:
    create_platform_tables()

    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)

    checks = []

    dashboard_response = client.get("/platform/app-build/dashboard")
    dashboard_text = dashboard_response.text

    dashboard_passed = (
        dashboard_response.status_code == 200
        and "Restore Plan" in dashboard_text
        and "workspaceRestorePlanPreview" in dashboard_text
        and "/restore-plan" in dashboard_text
    )
    checks.append(
        {
            "name": "dashboard_restore_plan_html",
            "passed": dashboard_passed,
            "status_code": dashboard_response.status_code,
        }
    )

    run_response = client.post(
        "/platform/app-build/run",
        json={
            "app_request": "Build me a simple ticketing app",
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

    if workflow_run_id:
        db = PlatformSessionLocal()
        try:
            detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
            persist_result = persist_generated_files_for_workflow(
                db,
                detail,
                workspace_id=f"workspace_{workflow_run_id}",
                project_id="project_version_restore_plan_check",
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
                        + "\\nCurrent DB preview changed after snapshot."
                    )
                    file_record.content_hash = (
                        "current_changed_for_restore_plan_"
                        + first_generated_file_id[-8:]
                    )
                    file_record.updated_at = utc_now()
                    db.commit()
        finally:
            db.close()

    snapshot_passed = (
        persist_result.get("success") is True
        and persist_result.get("persisted_file_count", 0) >= 1
        and bool(first_generated_file_id)
        and bool(first_version_id)
        and persist_result.get("disk_write_performed") is False
    )
    checks.append(
        {
            "name": "target_version_snapshot_created",
            "passed": snapshot_passed,
            "first_generated_file_id": first_generated_file_id,
            "first_version_id": first_version_id,
            "disk_write_performed": persist_result.get("disk_write_performed"),
        }
    )

    restore_plan_response = client.post(
        f"/platform/app-build/generated-file-versions/{first_version_id}/restore-plan"
    ) if first_version_id else None
    restore_plan_data = (
        restore_plan_response.json() if restore_plan_response is not None else {}
    )
    plan = restore_plan_data.get("restore_plan") or {}
    impact = plan.get("impact") or {}
    steps = plan.get("steps") or []

    restore_plan_passed = (
        restore_plan_response is not None
        and restore_plan_response.status_code == 200
        and restore_plan_data.get("success") is True
        and restore_plan_data.get("found") is True
        and restore_plan_data.get("restore_mode") == "plan_only"
        and restore_plan_data.get("write_mode") == "db_preview_only"
        and restore_plan_data.get("disk_write_performed") is False
        and restore_plan_data.get("db_mutation_performed") is False
        and plan.get("execution_supported") is False
        and plan.get("planned_action") == "replace_db_preview_content"
        and plan.get("manual_approval_required") is True
        and impact.get("hash_changed") is True
        and len(steps) == 1
        and steps[0].get("execution_status") == "not_executed"
    )
    checks.append(
        {
            "name": "restore_plan_created",
            "passed": restore_plan_passed,
            "status_code": restore_plan_response.status_code if restore_plan_response is not None else None,
            "restore_mode": restore_plan_data.get("restore_mode"),
            "planned_action": plan.get("planned_action"),
            "manual_approval_required": plan.get("manual_approval_required"),
            "disk_write_performed": restore_plan_data.get("disk_write_performed"),
            "db_mutation_performed": restore_plan_data.get("db_mutation_performed"),
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
    result = run_version_restore_planning_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
