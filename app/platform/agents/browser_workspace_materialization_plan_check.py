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
        "Approval-Gated Workspace Materialization Plan",
        "workspaceMaterializationPlan",
        "materializationPlanStatus",
        "materializationPlanFileCount",
        "materializationPlanSafetyMode",
        "materializationPlanWorkspaceRoot",
        "materializationPlanPaths",
        "workspaceMaterializationPlanResult",
        "buildWorkspaceMaterializationPlan",
        "clearWorkspaceMaterializationPlan",
        "buildWorkspaceMaterializationPlanPayload",
        "normalizeMaterializationRelativePath",
        "approval_gated_plan_only",
        "Plan only · approval required",
        "approval_required_before_execution",
        "materialization_execution_enabled: false",
        "generated_files_written_to_disk: false",
        "filesystem_write_performed: false",
        "disk_write_performed: false",
        "runtime_server_started: false",
        "preview_server_started: false",
        "generated_code_execution_performed: false",
        "repair_applied: false",
        "restore_executed: false",
        "plan_only_no_write",
        "db_preview_only",
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
            "name": "materialization_plan_safety_claims",
            "passed": "materialization_execution_enabled: false" in dashboard_text
            and "generated_files_written_to_disk: false" in dashboard_text
            and "filesystem_write_performed: false" in dashboard_text
            and "generated_code_execution_performed: false" in dashboard_text
            and "repair_applied: false" in dashboard_text,
        },
    ]

    passed = all(check.get("passed") for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "check": "browser_workspace_materialization_plan_check",
        "checks": checks,
    }


def main() -> int:
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
