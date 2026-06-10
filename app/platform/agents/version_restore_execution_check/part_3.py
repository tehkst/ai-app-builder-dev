# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import json
from typing import Any, Dict, List
from fastapi.testclient import TestClient
from app.main import app
from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.generated_file_persistence_service import (
    persist_generated_files_for_workflow,
)
from app.platform.services.generated_file_version_service import (
    create_generated_file_version_snapshot,
)
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail

def _execute_after_approval(
    client: TestClient,
    approval_id: str,
    expected_target_content: str,
) -> Dict[str, Any]:
    response = client.post(
        f"/platform/app-build/restore-approval-requests/{approval_id}/execute"
    )
    data = response.json()
    restore_result = data.get("restore_result") or {}
    execution_record = data.get("restore_execution_record") or {}
    pre_restore_snapshot = data.get("pre_restore_snapshot") or {}
    pre_restore_version = pre_restore_snapshot.get("generated_file_version") or {}
    post_restore_snapshot = data.get("post_restore_snapshot") or {}
    post_restore_version = post_restore_snapshot.get("generated_file_version") or {}

    return {
        "name": "approved_restore_executed_db_only",
        "passed": response.status_code == 200
        and data.get("restore_execution_performed") is True
        and data.get("db_content_mutation_performed") is True
        and data.get("disk_write_performed") is False
        and data.get("generated_code_execution_performed") is False
        and restore_result.get("after_content_preview") == expected_target_content
        and restore_result.get("target_restore_status") == "restored"
        and bool(execution_record.get("restore_execution_id"))
        and execution_record.get("execution_status") == "executed"
        and execution_record.get("restore_execution_performed") is True
        and execution_record.get("db_content_mutation_performed") is True
        and execution_record.get("disk_write_performed") is False
        and execution_record.get("generated_code_execution_performed") is False
        and pre_restore_snapshot.get("snapshot_created") is True
        and bool(pre_restore_snapshot.get("generated_file_version_id"))
        and pre_restore_version.get("snapshot_status")
        == "pre_restore_rollback_snapshot"
        and pre_restore_version.get("restore_status") == "rollback_point"
        and pre_restore_version.get("content_preview")
        == restore_result.get("before_content_preview")
        and pre_restore_snapshot.get("disk_write_performed") is False
        and post_restore_snapshot.get("snapshot_created") is True
        and bool(post_restore_snapshot.get("generated_file_version_id"))
        and post_restore_version.get("snapshot_status") == "restore_snapshot"
        and post_restore_version.get("restore_status") == "restore_result"
        and post_restore_version.get("content_preview") == expected_target_content
        and post_restore_snapshot.get("disk_write_performed") is False,
        "status_code": response.status_code,
        "restore_execution_performed": data.get("restore_execution_performed"),
        "db_content_mutation_performed": data.get("db_content_mutation_performed"),
        "disk_write_performed": data.get("disk_write_performed"),
        "generated_code_execution_performed": data.get(
            "generated_code_execution_performed"
        ),
        "target_restore_status": restore_result.get("target_restore_status"),
        "path": restore_result.get("path"),
        "restore_execution_id": execution_record.get("restore_execution_id"),
        "execution_status": execution_record.get("execution_status"),
        "pre_restore_snapshot_created": pre_restore_snapshot.get("snapshot_created"),
        "pre_restore_snapshot_version_id": pre_restore_snapshot.get(
            "generated_file_version_id"
        ),
        "pre_restore_snapshot_status": pre_restore_version.get("snapshot_status"),
        "pre_restore_snapshot_restore_status": pre_restore_version.get(
            "restore_status"
        ),
        "post_restore_snapshot_created": post_restore_snapshot.get("snapshot_created"),
        "post_restore_snapshot_version_id": post_restore_snapshot.get(
            "generated_file_version_id"
        ),
        "post_restore_snapshot_status": post_restore_version.get("snapshot_status"),
        "post_restore_snapshot_restore_status": post_restore_version.get(
            "restore_status"
        ),
    }

def run_check() -> Dict[str, Any]:
    create_platform_tables()
    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)

    checks: List[Dict[str, Any]] = []

    target_check = _create_target_version(client)
    checks.append(target_check)

    target_version_id = target_check.get("first_version_id")
    target_content = target_check.get("target_content")
    if not target_version_id or not target_content:
        return {
            "success": False,
            "passed": False,
            "checks": checks,
        }

    approval_check = _create_approval(client, target_version_id)
    checks.append(approval_check)

    approval_id = approval_check.get("approval_id")
    if not approval_id:
        return {
            "success": False,
            "passed": False,
            "checks": checks,
        }

    checks.append(_execute_before_approval(client, approval_id))
    checks.append(_approve_request(client, approval_id))
    checks.append(_execute_after_approval(client, approval_id, target_content))

    passed = all(check.get("passed") for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "workflow_run_id": target_check.get("workflow_run_id"),
        "first_generated_file_id": target_check.get("first_generated_file_id"),
        "first_version_id": target_version_id,
        "approval_id": approval_id,
        "checks": checks,
    }

if __name__ == "__main__":
    print(json.dumps(run_check(), indent=2, sort_keys=True))
