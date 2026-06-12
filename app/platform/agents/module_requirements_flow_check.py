from __future__ import annotations

import json
from typing import Any, Dict

from fastapi.testclient import TestClient

from app.main import app
from app.platform.api.security import require_platform_admin


def run_module_requirements_flow_check() -> Dict[str, Any]:
    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)
    checks = []

    created = client.post(
        "/platform/app-build/module/create",
        json={
            "module_name": "Billing Controls",
            "module_goal": "Add billing plan management for platform admins.",
            "acceptance_criteria": ["JWT admin only", "No rollout without approval"],
        },
    )
    created_data = created.json()
    request = created_data.get("request") or {}
    scope = created_data.get("requirements_scope") or {}
    checks.append(
        {
            "name": "create_generates_requirements_scope",
            "passed": (
                created.status_code == 200
                and created_data.get("success") is True
                and request.get("status") == "pending"
                and bool(request.get("request_id"))
                and bool(scope.get("scoping_request_id"))
                and scope.get("status") == "scope_ready"
                and created_data.get("generation_started") is False
            ),
        }
    )

    accepted = client.post(
        "/platform/app-build/module/scope/accept",
        json={
            "request_id": request.get("request_id"),
            "scoping_request_id": scope.get("scoping_request_id"),
        },
    )
    accepted_data = accepted.json()
    checks.append(
        {
            "name": "accept_scope_stops_before_generation",
            "passed": (
                accepted.status_code == 200
                and accepted_data.get("status") == "scope_accepted"
                and accepted_data.get("generation_started") is False
            ),
        }
    )

    amended = client.post(
        "/platform/app-build/module/scope/amend",
        json={
            "request_id": request.get("request_id"),
            "module_name": "Billing Controls",
            "module_goal": "Add billing plan and invoice management.",
            "acceptance_criteria": ["Admin can review invoices"],
        },
    )
    amended_data = amended.json()
    checks.append(
        {
            "name": "amend_regenerates_scope",
            "passed": (
                amended.status_code == 200
                and amended_data.get("success") is True
                and bool((amended_data.get("requirements_scope") or {}).get("scoping_request_id"))
            ),
        }
    )

    rejected = client.post(
        "/platform/app-build/module/scope/reject",
        json={"request_id": request.get("request_id"), "reason": "Needs rework."},
    )
    rejected_data = rejected.json()
    checks.append(
        {
            "name": "reject_scope_records_rework",
            "passed": rejected.status_code == 200 and rejected_data.get("status") == "scope_rejected",
        }
    )

    return {"success": all(check["passed"] for check in checks), "checks": checks}


def main() -> None:
    result = run_module_requirements_flow_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
