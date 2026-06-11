from __future__ import annotations

import json
from typing import Any, Dict

from fastapi.testclient import TestClient

from app.main import app
from app.platform.api.security import require_platform_admin


def run_scoping_gateway_check() -> Dict[str, Any]:
    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)
    checks = []

    incomplete = client.post(
        "/platform/app-build/scoping/analyze",
        json={
            "mode_selector": "Build New User App",
            "target_boundary": "New Independent Application Workspace",
            "change_classification": "New Feature",
            "app_idea": "Gym booking app",
        },
    )
    incomplete_data = incomplete.json()
    checks.append(
        {
            "name": "clarification_required",
            "passed": (
                incomplete.status_code == 200
                and incomplete_data.get("status") == "clarification_required"
                and bool(incomplete_data.get("questions"))
                and incomplete_data["safety_flags"]["writes_source_files"] is False
            ),
            "status_code": incomplete.status_code,
        }
    )

    complete_payload = {
        "mode_selector": "Build New User App",
        "target_boundary": "New Independent Application Workspace",
        "change_classification": "New Feature",
        "app_idea": "Build a gym booking app with slot capacity controls.",
        "target_users": ["gym goer", "gym manager"],
        "core_views": ["booking calendar", "manager capacity dashboard"],
        "data_entities": ["User", "TimeSlot", "Booking"],
        "auth_model": "Gym goers book slots; managers control capacity.",
        "success_criteria": ["booking prevents over-capacity", "manager sees usage"],
    }
    complete = client.post("/platform/app-build/scoping/analyze", json=complete_payload)
    complete_data = complete.json()
    checks.append(
        {
            "name": "scope_ready",
            "passed": (
                complete.status_code == 200
                and complete_data.get("status") == "scope_ready"
                and bool(complete_data.get("scoping_request_id"))
                and "Scope of Work" in complete_data.get("scope_of_work_markdown", "")
                and bool(complete_data.get("milestone_tree"))
                and complete_data.get("approval_required") is True
            ),
            "status_code": complete.status_code,
        }
    )

    approval = client.post(
        "/platform/app-build/scoping/approve",
        json={
            "scoping_request_id": complete_data.get("scoping_request_id"),
            "normalized_request": complete_data.get("normalized_request"),
            "scope_of_work_markdown": complete_data.get("scope_of_work_markdown"),
        },
    )
    approval_data = approval.json()
    checks.append(
        {
            "name": "approval_gate",
            "passed": (
                approval.status_code == 200
                and approval_data.get("approval_status") == "scope_approved"
                and approval_data.get("generation_started") is False
            ),
            "status_code": approval.status_code,
        }
    )

    recent = client.get("/platform/app-build/scoping/recent")
    recent_data = recent.json()
    requests = recent_data.get("requests") or []
    checks.append(
        {
            "name": "persistent_scope_history",
            "passed": (
                recent.status_code == 200
                and recent_data.get("success") is True
                and any(
                    item.get("scoping_request_id") == complete_data.get("scoping_request_id")
                    and item.get("approval_status") == "scope_approved"
                    for item in requests
                )
            ),
            "status_code": recent.status_code,
        }
    )

    return {"success": all(item["passed"] for item in checks), "checks": checks}


def main() -> None:
    result = run_scoping_gateway_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
