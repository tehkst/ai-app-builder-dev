from __future__ import annotations

import json
from typing import Any, Dict, List

from fastapi.testclient import TestClient

from app.main import app
from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.generated_file_persistence_service import persist_generated_files_for_workflow
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail


def _client() -> TestClient:
    create_platform_tables()
    app.dependency_overrides[require_platform_admin] = lambda: True
    return TestClient(app)


def _check_dashboard(client: TestClient) -> Dict[str, Any]:
    response = client.get("/platform/app-build/dashboard")
    text = response.text
    passed = all(token in text for token in [
        "Version History",
        "Create Version Snapshot",
        "Load Version History",
        "workspaceVersionList",
        "workspaceVersionPreview",
        "/generated-file-versions/",
        "/versions",
    ])
    return {"name": "dashboard_version_history_panel_html", "passed": response.status_code == 200 and passed, "status_code": response.status_code}


def _run_app_build(client: TestClient) -> Dict[str, Any]:
    response = client.post("/platform/app-build/run", json={"app_request": "Build me a simple CRM app", "real_bridge": True})
    data = response.json()
    workflow_run_id = (data.get("summary") or {}).get("workflow_run_id")
    return {
        "check": {"name": "workflow_run_created", "passed": response.status_code == 200 and data.get("success") is True and data.get("status") == "completed" and bool(workflow_run_id), "status_code": response.status_code, "workflow_run_id": workflow_run_id},
        "workflow_run_id": workflow_run_id,
    }


def _persist_generated_files(workflow_run_id: str) -> Dict[str, Any]:
    if not workflow_run_id:
        return {}
    db = PlatformSessionLocal()
    try:
        detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
        return persist_generated_files_for_workflow(db, detail, workspace_id=f"workspace_{workflow_run_id}", project_id="project_version_dashboard_check")
    finally:
        db.close()


def _check_persistence(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": "generated_files_persisted",
        "passed": result.get("success") is True and result.get("persisted_file_count", 0) >= 1 and result.get("disk_write_performed") is False,
        "persisted_file_count": result.get("persisted_file_count", 0),
        "disk_write_performed": result.get("disk_write_performed"),
    }


def _load_first_generated_file(client: TestClient, workflow_run_id: str) -> Dict[str, Any]:
    response = client.get(f"/platform/app-build/runs/{workflow_run_id}/persisted-files") if workflow_run_id else None
    data = response.json() if response is not None else {}
    files = data.get("generated_files") or []
    generated_file_id = files[0].get("generated_file_id") if files else None
    return {
        "check": {"name": "persisted_files_available_for_panel", "passed": response is not None and response.status_code == 200 and data.get("success") is True and data.get("persisted_file_count", 0) >= 1 and bool(generated_file_id), "status_code": response.status_code if response is not None else None, "first_generated_file_id": generated_file_id},
        "generated_file_id": generated_file_id,
    }


def _create_version(client: TestClient, generated_file_id: str) -> Dict[str, Any]:
    response = client.post(f"/platform/app-build/generated-files/{generated_file_id}/versions") if generated_file_id else None
    data = response.json() if response is not None else {}
    version_id = data.get("generated_file_version_id")
    return {
        "check": {"name": "single_file_version_snapshot_created", "passed": response is not None and response.status_code == 200 and data.get("success") is True and data.get("snapshot_created") is True and data.get("write_mode") == "db_preview_only" and data.get("disk_write_performed") is False and bool(version_id), "status_code": response.status_code if response is not None else None, "first_version_id": version_id},
        "version_id": version_id,
    }


def _check_version_history(client: TestClient, generated_file_id: str) -> Dict[str, Any]:
    response = client.get(f"/platform/app-build/generated-files/{generated_file_id}/versions") if generated_file_id else None
    data = response.json() if response is not None else {}
    return {"name": "version_history_available_for_panel", "passed": response is not None and response.status_code == 200 and data.get("success") is True and data.get("version_count", 0) >= 1 and data.get("disk_write_performed") is False, "status_code": response.status_code if response is not None else None, "version_count": data.get("version_count", 0)}


def _check_version_detail(client: TestClient, version_id: str) -> Dict[str, Any]:
    response = client.get(f"/platform/app-build/generated-file-versions/{version_id}") if version_id else None
    data = response.json() if response is not None else {}
    version = data.get("generated_file_version") or {}
    return {"name": "version_detail_available_for_panel", "passed": response is not None and response.status_code == 200 and data.get("success") is True and data.get("found") is True and version.get("restore_status") == "not_restored" and bool(version.get("content_preview")) and bool(version.get("content_hash")), "status_code": response.status_code if response is not None else None, "restore_status": version.get("restore_status")}


def run_version_history_dashboard_panel_check() -> Dict[str, Any]:
    client = _client()
    checks: List[Dict[str, Any]] = [_check_dashboard(client)]
    run = _run_app_build(client)
    checks.append(run["check"])
    workflow_run_id = run["workflow_run_id"]
    checks.append(_check_persistence(_persist_generated_files(workflow_run_id)))
    file_result = _load_first_generated_file(client, workflow_run_id)
    checks.append(file_result["check"])
    generated_file_id = file_result["generated_file_id"]
    version_result = _create_version(client, generated_file_id)
    checks.append(version_result["check"])
    version_id = version_result["version_id"]
    checks.append(_check_version_history(client, generated_file_id))
    checks.append(_check_version_detail(client, version_id))
    passed = all(check["passed"] for check in checks)
    return {"success": passed, "passed": passed, "checks": checks, "workflow_run_id": workflow_run_id, "first_generated_file_id": generated_file_id, "first_version_id": version_id}


def main() -> None:
    result = run_version_history_dashboard_panel_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
