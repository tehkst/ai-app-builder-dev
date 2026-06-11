from __future__ import annotations

import json
from typing import Any, Dict

from fastapi.testclient import TestClient

from app.main import app
from app.platform.api.security import require_platform_admin


def run_app_build_dashboard_check() -> Dict[str, Any]:
    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)

    checks = []

    dashboard_response = client.get("/platform/app-build/dashboard")
    dashboard_passed = (
        dashboard_response.status_code == 200
        and "AI Software Factory Platform Admin Console" in dashboard_response.text
        and "dashboard-overview" in dashboard_response.text
        and "Production Posture" in dashboard_response.text
        and "Self-Build Control Center" in dashboard_response.text
        and "Platform Admin JWT" in dashboard_response.text
        and "parseResponse" in dashboard_response.text
        and "Platform Function Builder" in dashboard_response.text
        and "Self-Build Scoping Gateway" in dashboard_response.text
        and "Infrastructure Migration" in dashboard_response.text
        and "Self-Healing Loop" in dashboard_response.text
        and "Run Clarification Check" in dashboard_response.text
        and "Confirm & Approve Scope" in dashboard_response.text
        and "Load Recent Scopes" in dashboard_response.text
        and "/platform/app-build/scoping/recent" in dashboard_response.text
        and "/platform/app-build/scoping/analyze" in dashboard_response.text
        and "Gym Booking App Demo" in dashboard_response.text
        and "runGymBookingDemo" in dashboard_response.text
        and "/platform/app-build/module-requests" in dashboard_response.text
        and "/platform/app-build/demo/gym-booking" in dashboard_response.text
        and "/platform/app-build/runs/recent" in dashboard_response.text
        and "/summary" in dashboard_response.text
        and "Generated Files" in dashboard_response.text
        and "/generated-files" in dashboard_response.text
        and "Workspace Explorer" in dashboard_response.text
        and "/persisted-files" in dashboard_response.text
        and "workspaceFileList" in dashboard_response.text
        and "Version History" in dashboard_response.text
        and "Create Version Snapshot" in dashboard_response.text
        and "/generated-file-versions/" in dashboard_response.text
        and "Version Diff Viewer" in dashboard_response.text
        and "workspaceVersionDiffPreview" in dashboard_response.text
        and "/diff/" in dashboard_response.text
        and "Restore Plan" in dashboard_response.text
        and "workspaceRestorePlanPreview" in dashboard_response.text
        and "/restore-plan" in dashboard_response.text
        and "Approval Workflow" in dashboard_response.text
        and "workspaceRestoreApprovalPreview" in dashboard_response.text
        and "/restore-approval-requests" in dashboard_response.text
        and "4A. Approve" in dashboard_response.text
        and "4B. Reject" in dashboard_response.text
        and "approveSelectedRestoreApproval" in dashboard_response.text
        and "rejectSelectedRestoreApproval" in dashboard_response.text
        and "decideSelectedRestoreApproval" in dashboard_response.text
        and "New App Build Session" not in dashboard_response.text
        and "App Specification Builder" not in dashboard_response.text
        and "Run App Build" not in dashboard_response.text
    )
    checks.append(
        {
            "name": "dashboard_html",
            "passed": dashboard_passed,
            "status_code": dashboard_response.status_code,
        }
    )

    css_response = client.get("/platform/app-build/app_build_dashboard.css")
    legacy_css_response = client.get("/platform/app-build/dashboard.css")
    css_passed = (
        css_response.status_code == 200
        and legacy_css_response.status_code == 200
        and "admin-shell" in css_response.text
        and "admin-sidebar" in css_response.text
        and "command-card" in css_response.text
        and 'href="app_build_dashboard.css"' in dashboard_response.text
    )
    checks.append(
        {
            "name": "dashboard_css",
            "passed": css_passed,
            "status_code": css_response.status_code,
        }
    )

    module_response = client.post(
        "/platform/app-build/module-requests",
        json={
            "module_name": "Billing and payments module",
            "module_goal": "Add approval-gated billing administration.",
            "acceptance_criteria": [
                "Admin-only access",
                "Approval-gated rollout",
                "Python 3.9 compatible tests",
            ],
        },
    )
    module_data = module_response.json()
    request_id = (module_data.get("request") or {}).get("request_id")

    module_passed = (
        module_response.status_code == 200
        and module_data.get("success") is True
        and bool(request_id)
        and module_data.get("safety_flags", {}).get("request_tracking_only") is True
    )
    checks.append(
        {
            "name": "create_platform_function_request",
            "passed": module_passed,
            "status_code": module_response.status_code,
            "request_id": request_id,
        }
    )

    request_passed = False
    request_status_code = None
    if request_id:
        request_response = client.get(
            f"/platform/app-build/module-requests/{request_id}"
        )
        request_status_code = request_response.status_code
        request_data = request_response.json()
        request_passed = (
            request_response.status_code == 200
            and request_data.get("success") is True
            and request_data.get("request_id") == request_id
            and (request_data.get("request") or {}).get("module_name")
            == "Billing and payments module"
        )

    checks.append(
        {
            "name": "load_platform_function_request",
            "passed": request_passed,
            "status_code": request_status_code,
            "request_id": request_id,
        }
    )

    list_response = client.get("/platform/app-build/module-requests")
    list_data = list_response.json()
    module_requests = list_data.get("requests") or []
    list_passed = (
        list_response.status_code == 200
        and list_data.get("success") is True
        and isinstance(module_requests, list)
        and any(item.get("request_id") == request_id for item in module_requests)
    )
    checks.append(
        {
            "name": "list_platform_function_requests",
            "passed": list_passed,
            "status_code": list_response.status_code,
            "returned_count": len(module_requests),
        }
    )

    passed = all(check["passed"] for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "checks": checks,
        "request_id": request_id,
    }


def main() -> None:
    result = run_app_build_dashboard_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
