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

def _execute_before_approval(client: TestClient, approval_id: str) -> Dict[str, Any]:
    response = client.post(
        f"/platform/app-build/restore-approval-requests/{approval_id}/execute"
    )
    data = response.json()

    execution_record = data.get("restore_execution_record") or {}

    return {
        "name": "restore_not_executed_before_approval",
        "passed": response.status_code == 200
        and data.get("restore_execution_performed") is False
        and data.get("db_content_mutation_performed") is False
        and data.get("disk_write_performed") is False
        and data.get("generated_code_execution_performed") is False
        and "not approved" in (data.get("reason") or "")
        and bool(execution_record.get("restore_execution_id"))
        and execution_record.get("execution_status") == "blocked"
        and execution_record.get("restore_execution_performed") is False,
        "status_code": response.status_code,
        "reason": data.get("reason"),
        "restore_execution_performed": data.get("restore_execution_performed"),
        "db_content_mutation_performed": data.get("db_content_mutation_performed"),
        "disk_write_performed": data.get("disk_write_performed"),
        "generated_code_execution_performed": data.get(
            "generated_code_execution_performed"
        ),
        "restore_execution_id": execution_record.get("restore_execution_id"),
        "execution_status": execution_record.get("execution_status"),
    }

def _approve_request(client: TestClient, approval_id: str) -> Dict[str, Any]:
    response = client.post(
        f"/platform/app-build/restore-approval-requests/{approval_id}/approve",
        json={
            "approver_id": "platform_admin",
            "decision_note": "Approved for V43 safe DB restore execution check.",
        },
    )
    data = response.json()
    approval_request = data.get("approval_request") or {}

    return {
        "name": "approval_request_approved",
        "passed": response.status_code == 200
        and data.get("decision_applied") is True
        and approval_request.get("status") == "approved"
        and data.get("restore_execution_performed") is False,
        "status_code": response.status_code,
        "approval_status": approval_request.get("status"),
        "decision_applied": data.get("decision_applied"),
        "restore_execution_performed": data.get("restore_execution_performed"),
    }
