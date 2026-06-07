from __future__ import annotations

import json
from typing import Any, Dict, List

from fastapi.testclient import TestClient

from app.main import app
from app.platform.api.security import require_platform_admin


def run_check() -> Dict[str, Any]:
    app.dependency_overrides[require_platform_admin] = lambda: True

    client = TestClient(app)
    response = client.get("/platform/app-build/dashboard")
    dashboard_text = response.text

    required_markers: List[str] = [
        "Persistent Approval Record",
        "persistentMaterializationApprovalRecord",
        "persistentApprovalRecordStatus",
        "persistentApprovalRecordId",
        "persistentApprovalRecordFile",
        "persistentApprovalRecordSafety",
        "persistentApprovalRecordResult",
        "createPersistentMaterializationApprovalRecord",
        "loadLatestPersistentMaterializationApprovalRecord",
        "clearPersistentMaterializationApprovalRecord",
        "renderPersistentMaterializationApprovalRecord",
        "/materialization-approval-records",
        "/materialization-approval-records/latest",
        "persistent_record_only_no_write_capability",
        "Record only · no write capability",
        "approval_record_only",
        "approval_grants_filesystem_write_capability: false",
        "materialization_execution_enabled: false",
        "generated_files_written_to_disk: false",
        "filesystem_write_performed: false",
        "disk_write_performed: false",
        "runtime_server_started: false",
        "preview_server_started: false",
        "generated_code_execution_performed: false",
        "repair_applied: false",
        "restore_executed: false",
    ]

    checks = [
        {
            "name": "dashboard_loaded",
            "passed": response.status_code == 200,
            "status_code": response.status_code,
        },
        *[
            {
                "name": f"marker_present::{marker}",
                "passed": marker in dashboard_text,
            }
            for marker in required_markers
        ],
        {
            "name": "v61_panel_safety_language",
            "passed": "does not execute materialization" in dashboard_text
            and "write files" in dashboard_text
            and "execute generated code" in dashboard_text,
        },
        {
            "name": "v60_approval_history_preserved",
            "passed": "Materialization Approval History" in dashboard_text
            and "recordMaterializationApprovalHistory" in dashboard_text
            and "history_only_no_write_capability" in dashboard_text,
        },
        {
            "name": "v59_approval_workflow_preserved",
            "passed": "Materialization Approval Workflow" in dashboard_text
            and "approveMaterializationPlan" in dashboard_text
            and "ui_state_only_no_write_capability" in dashboard_text,
        },
        {
            "name": "v58_materialization_plan_preserved",
            "passed": "Approval-Gated Workspace Materialization Plan" in dashboard_text
            and "buildWorkspaceMaterializationPlan" in dashboard_text
            and "approval_gated_plan_only" in dashboard_text,
        },
        {
            "name": "v57_static_preview_preserved",
            "passed": "Safe Static Preview Renderer" in dashboard_text
            and "renderSafeStaticPreview" in dashboard_text
            and "sanitized_db_preview_only" in dashboard_text,
        },
        {
            "name": "v56_results_review_preserved",
            "passed": "App Build Results Review" in dashboard_text
            and "refreshAppBuildResultsReview" in dashboard_text
            and "appBuildReviewRuntimeServer" in dashboard_text,
        },
        {
            "name": "v55_spec_builder_preserved",
            "passed": "App Specification Builder" in dashboard_text
            and "generateAppSpecificationPrompt" in dashboard_text
            and "useGeneratedAppSpecificationForSession" in dashboard_text,
        },
        {
            "name": "v54_launcher_preserved",
            "passed": "New App Build Session" in dashboard_text
            and "launchNewAppBuildSession" in dashboard_text
            and "newAppIdea" in dashboard_text,
        },
        {
            "name": "persistent_record_safety_claims",
            "passed": "approval_grants_filesystem_write_capability: false" in dashboard_text
            and "materialization_execution_enabled: false" in dashboard_text
            and "generated_files_written_to_disk: false" in dashboard_text
            and "filesystem_write_performed: false" in dashboard_text
            and "generated_code_execution_performed: false" in dashboard_text
            and "repair_applied: false" in dashboard_text
            and "restore_executed: false" in dashboard_text,
        },
    ]

    passed = all(check.get("passed") for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "check": "browser_materialization_persistent_approval_record_check",
        "checks": checks,
    }


def main() -> int:
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
