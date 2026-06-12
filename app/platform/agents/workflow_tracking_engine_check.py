from __future__ import annotations

import json
from typing import Any, Dict

from fastapi.testclient import TestClient

from app.main import app
from app.platform.api.security import require_platform_admin


def run_workflow_tracking_engine_check() -> Dict[str, Any]:
    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)
    checks = []

    created = client.post(
        "/platform/app-build/workflow-tracker/start",
        json={"requirements_text": "Add admin billing controls with approval gated rollout."},
    )
    created_data = created.json()
    workflow_id = created_data.get("workflow_id")
    checks.append(
        {
            "name": "start_scopes_and_waits_for_approval",
            "passed": created.status_code == 200
            and created_data.get("state") == "AWAITING_APPROVAL"
            and "Scope of Work" in created_data.get("scope_markdown", "")
            and bool(workflow_id),
        }
    )

    approved = client.post(
        "/platform/app-build/workflow-tracker/confirm-code",
        json={"workflow_id": workflow_id},
    )
    approved_data = approved.json()
    checks.append(
        {
            "name": "confirm_generates_tests_and_waits_for_deployment",
            "passed": approved.status_code == 200
            and approved_data.get("state") == "AWAITING_DEPLOYMENT"
            and "Paste this code into GitHub" in approved_data.get("manual_deploy_instructions", "")
            and approved_data.get("github_push_performed") is False,
        }
    )

    stuck = client.post(
        "/platform/app-build/workflow-tracker/start",
        json={"requirements_text": "Create a safe admin audit export."},
    ).json()
    healed = client.post(
        "/platform/app-build/workflow-tracker/self-heal",
        json={"workflow_id": stuck.get("workflow_id"), "target_state": "AWAITING_APPROVAL"},
    )
    healed_data = healed.json()
    checks.append(
        {
            "name": "self_heal_rolls_back_to_approval",
            "passed": healed.status_code == 200
            and healed_data.get("state") == "AWAITING_APPROVAL"
            and healed_data.get("cache_cleared") is True
            and healed_data.get("memory_buffer_rolled_back") is True,
        }
    )

    dashboard = client.get("/platform/app-build/dashboard")
    checks.append(
        {
            "name": "dashboard_contains_workflow_visualizer",
            "passed": dashboard.status_code == 200
            and "Workflow Tracking Engine" in dashboard.text
            and "Self-Heal / Refresh Code Execution" in dashboard.text
            and "/platform/app-build/workflow-tracker/start" in dashboard.text,
        }
    )

    return {"success": all(item["passed"] for item in checks), "checks": checks}


def main() -> None:
    result = run_workflow_tracking_engine_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
