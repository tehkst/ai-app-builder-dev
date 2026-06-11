from __future__ import annotations

import json
from typing import Any, Dict

from fastapi.testclient import TestClient

from app.main import app
from app.platform.api.security import require_platform_admin


def run_check() -> Dict[str, Any]:
    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)
    checks = []

    demo_response = client.post(
        "/platform/app-build/demo/gym-booking",
        json={"created_by": "gym_owner_demo_user"},
    )
    demo_data = demo_response.json()
    workflow_run_id = demo_data.get("workflow_run_id")
    user_activity = demo_data.get("user_activity") or {}
    safety_flags = demo_data.get("safety_flags") or {}
    checks.append(
        {
            "name": "demo_run_created",
            "passed": demo_response.status_code == 200
            and demo_data.get("success") is True
            and user_activity.get("active_user_count") == 1
            and bool(workflow_run_id)
            and safety_flags.get("disk_write_performed") is False
            and safety_flags.get("generated_code_execution_performed") is False,
            "status_code": demo_response.status_code,
            "workflow_run_id": workflow_run_id,
        }
    )

    files_response = client.get(
        f"/platform/app-build/runs/{workflow_run_id}/persisted-files"
    )
    files_data = files_response.json()
    paths = {
        item.get("path")
        for item in files_data.get("generated_files") or []
    }
    checks.append(
        {
            "name": "manager_and_goer_surfaces_persisted",
            "passed": files_response.status_code == 200
            and {"manager.html", "gym-goer.html"}.issubset(paths)
            and files_data.get("write_mode") == "db_preview_only",
            "status_code": files_response.status_code,
            "paths": sorted(paths),
        }
    )

    summary_response = client.get(
        f"/platform/app-build/runs/{workflow_run_id}/summary"
    )
    summary_data = summary_response.json()
    checks.append(
        {
            "name": "platform_admin_summary_visible",
            "passed": summary_response.status_code == 200
            and summary_data.get("workflow_name") == "Gym Booking App Demo"
            and summary_data.get("completed_step_count") == 3,
            "status_code": summary_response.status_code,
        }
    )

    passed = all(check["passed"] for check in checks)
    return {
        "success": passed,
        "passed": passed,
        "check": "gym_booking_demo_check",
        "checks": checks,
        "workflow_run_id": workflow_run_id,
    }


def main() -> int:
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
