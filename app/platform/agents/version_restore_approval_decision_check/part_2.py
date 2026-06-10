# Split from the legacy module to keep each Python file under 200 lines.
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

def run_version_restore_approval_decision_check() -> Dict[str, Any]:
    create_platform_tables()

    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)

    checks = []

    dashboard_response = client.get("/platform/app-build/dashboard")
    dashboard_text = dashboard_response.text

    dashboard_passed = (
        dashboard_response.status_code == 200
        and "Approve Request" in dashboard_text
        and "Reject Request" in dashboard_text
        and "approveSelectedRestoreApproval" in dashboard_text
        and "rejectSelectedRestoreApproval" in dashboard_text
        and "decideSelectedRestoreApproval" in dashboard_text
    )
    checks.append(
        {
            "name": "dashboard_restore_approval_decision_html",
            "passed": dashboard_passed,
            "status_code": dashboard_response.status_code,
        }
    )

    approval_context = _create_approval(client)
    approval_id = approval_context.get("approval_id")

    approval_created_passed = (
        bool(approval_context.get("workflow_run_id"))
        and bool(approval_context.get("first_generated_file_id"))
        and bool(approval_context.get("first_version_id"))
        and bool(approval_id)
        and approval_context["approval_data"].get("approval_created") is True
        and approval_context["approval_data"].get("restore_execution_performed") is False
        and approval_context["persist_result"].get("disk_write_performed") is False
    )
    checks.append(
        {
            "name": "approval_request_created_for_decision",
            "passed": approval_created_passed,
            "approval_id": approval_id,
        }
    )

    approve_response = client.post(
        f"/platform/app-build/restore-approval-requests/{approval_id}/approve",
        json={
            "approver_id": "platform_admin_check",
            "decision_note": "Approved in smoke check without restore execution.",
        },
    ) if approval_id else None
    approve_data = approve_response.json() if approve_response is not None else {}
    approved_approval = approve_data.get("approval_request") or {}

    approve_passed = (
        approve_response is not None
        and approve_response.status_code == 200
        and approve_data.get("success") is True
        and approve_data.get("found") is True
        and approve_data.get("decision") == "approved"
        and approve_data.get("decision_applied") is True
        and approve_data.get("restore_mode") == "approval_decision_only"
        and approve_data.get("write_mode") == "db_preview_only"
        and approve_data.get("disk_write_performed") is False
        and approve_data.get("db_content_mutation_performed") is False
        and approve_data.get("restore_execution_performed") is False
        and approved_approval.get("status") == "approved"
        and approved_approval.get("approver_id") == "platform_admin_check"
        and bool(approved_approval.get("decided_at"))
    )
    checks.append(
        {
            "name": "approval_request_approved_without_restore_execution",
            "passed": approve_passed,
            "status_code": approve_response.status_code if approve_response is not None else None,
            "approval_status": approved_approval.get("status"),
            "restore_execution_performed": approve_data.get("restore_execution_performed"),
        }
    )

    second_context = _create_approval(client)
    second_approval_id = second_context.get("approval_id")

    reject_response = client.post(
        f"/platform/app-build/restore-approval-requests/{second_approval_id}/reject",
        json={
            "approver_id": "platform_admin_check",
            "decision_note": "Rejected in smoke check without restore execution.",
        },
    ) if second_approval_id else None
    reject_data = reject_response.json() if reject_response is not None else {}
    rejected_approval = reject_data.get("approval_request") or {}

    reject_passed = (
        reject_response is not None
        and reject_response.status_code == 200
        and reject_data.get("success") is True
        and reject_data.get("found") is True
        and reject_data.get("decision") == "rejected"
        and reject_data.get("decision_applied") is True
        and reject_data.get("restore_mode") == "approval_decision_only"
        and reject_data.get("write_mode") == "db_preview_only"
        and reject_data.get("disk_write_performed") is False
        and reject_data.get("db_content_mutation_performed") is False
        and reject_data.get("restore_execution_performed") is False
        and rejected_approval.get("status") == "rejected"
        and rejected_approval.get("approver_id") == "platform_admin_check"
        and bool(rejected_approval.get("decided_at"))
    )
    checks.append(
        {
            "name": "approval_request_rejected_without_restore_execution",
            "passed": reject_passed,
            "status_code": reject_response.status_code if reject_response is not None else None,
            "approval_status": rejected_approval.get("status"),
            "restore_execution_performed": reject_data.get("restore_execution_performed"),
        }
    )

    repeat_approve_response = client.post(
        f"/platform/app-build/restore-approval-requests/{approval_id}/approve",
        json={
            "approver_id": "platform_admin_check",
            "decision_note": "Repeated approval should not apply.",
        },
    ) if approval_id else None
    repeat_approve_data = (
        repeat_approve_response.json() if repeat_approve_response is not None else {}
    )

    repeat_decision_passed = (
        repeat_approve_response is not None
        and repeat_approve_response.status_code == 200
        and repeat_approve_data.get("success") is True
        and repeat_approve_data.get("found") is True
        and repeat_approve_data.get("decision_applied") is False
        and repeat_approve_data.get("restore_execution_performed") is False
    )
    checks.append(
        {
            "name": "repeat_decision_is_not_reapplied",
            "passed": repeat_decision_passed,
            "status_code": repeat_approve_response.status_code if repeat_approve_response is not None else None,
            "decision_applied": repeat_approve_data.get("decision_applied"),
        }
    )

    passed = all(check["passed"] for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "checks": checks,
        "approval_id": approval_id,
        "second_approval_id": second_approval_id,
    }
