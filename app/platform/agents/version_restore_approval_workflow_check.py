from __future__ import annotations

import json
from typing import Any, Dict, List

from fastapi.testclient import TestClient

from app.main import app
from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformGeneratedFile, utc_now
from app.platform.services.generated_file_persistence_service import persist_generated_files_for_workflow
from app.platform.services.generated_file_version_service import create_generated_file_version_snapshot
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail


def _client() -> TestClient:
    create_platform_tables()
    app.dependency_overrides[require_platform_admin] = lambda: True
    return TestClient(app)


def _check_dashboard(client: TestClient) -> Dict[str, Any]:
    response = client.get("/platform/app-build/dashboard")
    text = response.text
    passed = response.status_code == 200 and all(token in text for token in [
        "Approval Workflow",
        "workspaceRestoreApprovalPreview",
        "/restore-approval-requests",
    ])
    return {"name": "dashboard_restore_approval_workflow_html", "passed": passed, "status_code": response.status_code}


def _run_app_build(client: TestClient) -> Dict[str, Any]:
    response = client.post("/platform/app-build/run", json={"app_request": "Build me a simple helpdesk app", "real_bridge": True})
    data = response.json()
    workflow_run_id = (data.get("summary") or {}).get("workflow_run_id")
    return {
        "check": {"name": "workflow_run_created", "passed": response.status_code == 200 and data.get("success") is True and data.get("status") == "completed" and bool(workflow_run_id), "status_code": response.status_code, "workflow_run_id": workflow_run_id},
        "workflow_run_id": workflow_run_id,
    }


def _create_target_snapshot(workflow_run_id: str) -> Dict[str, Any]:
    if not workflow_run_id:
        return {"persist_result": {}, "generated_file_id": None, "version_id": None}
    db = PlatformSessionLocal()
    try:
        detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
        persist_result = persist_generated_files_for_workflow(db, detail, workspace_id=f"workspace_{workflow_run_id}", project_id="project_restore_approval_check")
        generated_files = persist_result.get("generated_files") or []
        generated_file_id = generated_files[0].get("generated_file_id") if generated_files else None
        version_id = _snapshot_and_mutate_file(db, generated_file_id)
        return {"persist_result": persist_result, "generated_file_id": generated_file_id, "version_id": version_id}
    finally:
        db.close()


def _snapshot_and_mutate_file(db, generated_file_id: str):
    if not generated_file_id:
        return None
    snapshot = create_generated_file_version_snapshot(db, generated_file_id)
    file_record = db.query(PlatformGeneratedFile).filter(PlatformGeneratedFile.generated_file_id == generated_file_id).first()
    if file_record:
        file_record.content_preview = (
            (file_record.content_preview or "")
            + "\nCurrent DB preview changed before approval request."
        )
        file_record.content_hash = "current_changed_for_restore_approval_" + generated_file_id[-8:]
        file_record.updated_at = utc_now()
        db.commit()
    return snapshot.get("generated_file_version_id")


def _check_snapshot(context: Dict[str, Any]) -> Dict[str, Any]:
    persist_result = context["persist_result"]
    return {
        "name": "target_version_snapshot_created",
        "passed": persist_result.get("success") is True and persist_result.get("persisted_file_count", 0) >= 1 and bool(context["generated_file_id"]) and bool(context["version_id"]) and persist_result.get("disk_write_performed") is False,
        "first_generated_file_id": context["generated_file_id"],
        "first_version_id": context["version_id"],
        "disk_write_performed": persist_result.get("disk_write_performed"),
    }


def _create_restore_approval(client: TestClient, version_id: str) -> Dict[str, Any]:
    response = client.post(f"/platform/app-build/generated-file-versions/{version_id}/restore-approval-requests") if version_id else None
    data = response.json() if response is not None else {}
    approval = data.get("approval_request") or {}
    payload = approval.get("action_payload") or {}
    approval_id = approval.get("approval_id")
    passed = response is not None and response.status_code == 200 and data.get("success") is True and data.get("found") is True and data.get("approval_created") is True
    passed = passed and data.get("restore_mode") == "approval_only" and data.get("write_mode") == "db_preview_only" and data.get("disk_write_performed") is False
    passed = passed and data.get("db_content_mutation_performed") is False and data.get("restore_execution_performed") is False and approval.get("status") == "pending"
    passed = passed and approval.get("risk_level") == "high" and approval.get("action_type") == "approve_restore_plan_only" and payload.get("execution_supported") is False
    return {"check": {"name": "restore_approval_request_created", "passed": passed and bool(approval_id), "status_code": response.status_code if response is not None else None, "approval_id": approval_id, "approval_status": approval.get("status"), "restore_execution_performed": data.get("restore_execution_performed")}, "approval_id": approval_id}


def _check_loaded_approval(client: TestClient, approval_id: str) -> Dict[str, Any]:
    response = client.get(f"/platform/app-build/restore-approval-requests/{approval_id}") if approval_id else None
    data = response.json() if response is not None else {}
    approval = data.get("approval_request") or {}
    passed = response is not None and response.status_code == 200 and data.get("success") is True and data.get("found") is True
    passed = passed and data.get("restore_mode") == "approval_only" and data.get("disk_write_performed") is False
    passed = passed and data.get("db_content_mutation_performed") is False and data.get("restore_execution_performed") is False
    return {"name": "restore_approval_request_retrieved", "passed": passed and approval.get("approval_id") == approval_id and approval.get("status") == "pending", "status_code": response.status_code if response is not None else None, "approval_id": approval.get("approval_id"), "approval_status": approval.get("status")}


def run_version_restore_approval_workflow_check() -> Dict[str, Any]:
    client = _client()
    checks: List[Dict[str, Any]] = [_check_dashboard(client)]
    run = _run_app_build(client)
    checks.append(run["check"])
    workflow_run_id = run["workflow_run_id"]
    snapshot_context = _create_target_snapshot(workflow_run_id)
    checks.append(_check_snapshot(snapshot_context))
    approval = _create_restore_approval(client, snapshot_context["version_id"])
    checks.append(approval["check"])
    approval_id = approval["approval_id"]
    checks.append(_check_loaded_approval(client, approval_id))
    passed = all(check["passed"] for check in checks)
    return {"success": passed, "passed": passed, "checks": checks, "workflow_run_id": workflow_run_id, "first_generated_file_id": snapshot_context["generated_file_id"], "first_version_id": snapshot_context["version_id"], "approval_id": approval_id}


def main() -> None:
    result = run_version_restore_approval_workflow_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
