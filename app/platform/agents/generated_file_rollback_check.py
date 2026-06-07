from __future__ import annotations

import json
from typing import Any, Dict

from fastapi.testclient import TestClient

from app.main import app
from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import PlatformSessionLocal
from app.platform.services.generated_file_rollback_service import (
    build_workflow_rollback_plan,
)
from app.platform.services.workflow_run_persistence_service import (
    get_workflow_run_detail,
)


def run_generated_file_rollback_check() -> Dict[str, Any]:
    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)

    run_response = client.post(
        "/platform/app-build/run",
        json={
            "app_request": "Build me a booking app for yoga classes",
            "real_bridge": True,
        },
    )
    run_data = run_response.json()
    workflow_run_id = (run_data.get("summary") or {}).get("workflow_run_id")

    db = PlatformSessionLocal()
    try:
        detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
        rollback_plan = build_workflow_rollback_plan(detail)
    finally:
        db.close()

    rollback_steps = rollback_plan.get("rollback_steps") or []

    checks = [
        {
            "name": "workflow_run_created",
            "passed": run_response.status_code == 200 and bool(workflow_run_id),
            "status_code": run_response.status_code,
            "workflow_run_id": workflow_run_id,
        },
        {
            "name": "rollback_plan_created",
            "passed": rollback_plan.get("success") is True,
        },
        {
            "name": "generated_files_detected",
            "passed": rollback_plan.get("generated_file_count") == 5,
            "generated_file_count": rollback_plan.get("generated_file_count"),
        },
        {
            "name": "preview_only_no_manual_approval",
            "passed": rollback_plan.get("manual_approval_required") is False,
            "manual_approval_required": rollback_plan.get("manual_approval_required"),
        },
        {
            "name": "all_steps_are_no_op_preview_only",
            "passed": all(
                step.get("rollback_action") == "no_op_preview_only"
                for step in rollback_steps
            ),
            "rollback_step_count": len(rollback_steps),
        },
    ]

    passed = all(check["passed"] for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "checks": checks,
        "workflow_run_id": workflow_run_id,
        "rollback_plan": rollback_plan,
    }


def main() -> None:
    result = run_generated_file_rollback_check()
    print(json.dumps(result, indent=2, sort_keys=True))

    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
