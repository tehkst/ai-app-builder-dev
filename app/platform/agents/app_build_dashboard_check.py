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
        and "AI Software Factory App Build Dashboard" in dashboard_response.text
        and "/platform/app-build/run" in dashboard_response.text
        and "/platform/app-build/runs/recent" in dashboard_response.text
        and "/summary" in dashboard_response.text
        and "Generated Files" in dashboard_response.text
        and "/generated-files" in dashboard_response.text
    )
    checks.append(
        {
            "name": "dashboard_html",
            "passed": dashboard_passed,
            "status_code": dashboard_response.status_code,
        }
    )

    run_response = client.post(
        "/platform/app-build/run",
        json={
            "app_request": "Build me a booking app for yoga classes",
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
            "name": "run_app_build",
            "passed": run_passed,
            "status_code": run_response.status_code,
            "workflow_run_id": workflow_run_id,
        }
    )

    summary_passed = False
    summary_status_code = None
    if workflow_run_id:
        summary_response = client.get(
            f"/platform/app-build/runs/{workflow_run_id}/summary"
        )
        summary_status_code = summary_response.status_code
        summary_data = summary_response.json()
        summary_passed = (
            summary_response.status_code == 200
            and summary_data.get("success") is True
            and summary_data.get("found") is True
            and summary_data.get("summary") is True
            and summary_data.get("workflow_run_id") == workflow_run_id
        )

    checks.append(
        {
            "name": "run_summary",
            "passed": summary_passed,
            "status_code": summary_status_code,
            "workflow_run_id": workflow_run_id,
        }
    )

    recent_response = client.get("/platform/app-build/runs/recent?limit=5")
    recent_data = recent_response.json()
    recent_runs = recent_data.get("workflow_runs") or []
    recent_passed = (
        recent_response.status_code == 200
        and recent_data.get("success") is True
        and isinstance(recent_runs, list)
        and len(recent_runs) >= 1
    )
    checks.append(
        {
            "name": "recent_runs",
            "passed": recent_passed,
            "status_code": recent_response.status_code,
            "returned_count": len(recent_runs),
        }
    )

    passed = all(check["passed"] for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "checks": checks,
        "workflow_run_id": workflow_run_id,
    }


def main() -> None:
    result = run_app_build_dashboard_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
