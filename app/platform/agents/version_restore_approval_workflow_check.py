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


def run_version_restore_approval_workflow_check() -> Dict[str, Any]:
    create_platform_tables()

    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)

    checks = []

    dashboard_response = client.get("/platform/app-build/dashboard")
    dashboard_text = dashboard_response.text

    dashboard_passed = (
        dashboard_response.status_code == 200
        and "Approval Workflow" in dashboard_text
        and "workspaceRestoreApprovalPreview" in dashboard_text
        and "/restore-approval-requests" in dashboard_text
    )
    checks.append(
        {
            "name": "dashboard_restore_approval_workflow_html",
            "passed": dashboard_passed,
            "status_code": dashboard_response.status_code,
        }
    )

    run_response = client.post(
        "/platform/app-build/run",
        json={
            "app_request": "Build me a simple helpdesk app",
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
                project_id="project_restore_approval_check",
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
                        + "\\nCurrent DB preview changed before approval request."
                    )
                    file_record.content_hash = (
                        "current_changed_for_restore_approval_"
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

    approval_response = client.post(
        f"/platform/app-build/generated-file-versions/{first_version_id}/restore-approval-requests"
    ) if first_version_id else None
    approval_data = approval_response.json() if approval_response is not None else {}
    approval = approval_data.get("approval_request") or {}
    action_payload = approval.get("action_payload") or {}
    approval_id = approval.get("approval_id")

    approval_created_passed = (
        approval_response is not None
        and approval_response.status_code == 200
        and approval_data.get("success") is True
        and approval_data.get("found") is True
        and approval_data.get("approval_created") is True
        and approval_data.get("restore_mode") == "approval_only"
        and approval_data.get("write_mode") == "db_preview_only"
        and approval_data.get("disk_write_performed") is False
        and approval_data.get("db_content_mutation_performed") is False
        and approval_data.get("restore_execution_performed") is False
        and approval.get("status") == "pending"
        and approval.get("risk_level") == "high"
        and approval.get("action_type") == "approve_restore_plan_only"
        and action_payload.get("execution_supported") is False
        and action_payload.get("restore_execution_performed") is False
        and bool(approval_id)
    )
    checks.append(
        {
            "name": "restore_approval_request_created",
            "passed": approval_created_passed,
            "status_code": approval_response.status_code if approval_response is not None else None,
            "approval_id": approval_id,
            "approval_status": approval.get("status"),
            "restore_execution_performed": approval_data.get("restore_execution_performed"),
        }
    )

    get_approval_response = client.get(
        f"/platform/app-build/restore-approval-requests/{approval_id}"
    ) if approval_id else None
    get_approval_data = (
        get_approval_response.json() if get_approval_response is not None else {}
    )
    loaded_approval = get_approval_data.get("approval_request") or {}

    get_approval_passed = (
        get_approval_response is not None
        and get_approval_response.status_code == 200
        and get_approval_data.get("success") is True
        and get_approval_data.get("found") is True
        and get_approval_data.get("restore_mode") == "approval_only"
        and get_approval_data.get("disk_write_performed") is False
        and get_approval_data.get("db_content_mutation_performed") is False
        and get_approval_data.get("restore_execution_performed") is False
        and loaded_approval.get("approval_id") == approval_id
        and loaded_approval.get("status") == "pending"
    )
    checks.append(
        {
            "name": "restore_approval_request_retrieved",
            "passed": get_approval_passed,
            "status_code": get_approval_response.status_code if get_approval_response is not None else None,
            "approval_id": loaded_approval.get("approval_id"),
            "approval_status": loaded_approval.get("status"),
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
        "approval_id": approval_id,
    }


def main() -> None:
    result = run_version_restore_approval_workflow_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
