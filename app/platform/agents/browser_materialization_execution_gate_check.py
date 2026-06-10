from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.platform.api import app_build_routes
from app.platform.api.security import require_platform_admin


def _override_admin() -> bool:
    return True


def _check_marker(html: str, marker: str) -> Dict[str, Any]:
    return {
        "name": f"marker_present::{marker}",
        "passed": marker in html,
    }


def main() -> int:
    app = FastAPI()
    app.include_router(app_build_routes.router)
    app.dependency_overrides[require_platform_admin] = _override_admin

    client = TestClient(app)
    response = client.get("/platform/app-build/dashboard")

    checks: List[Dict[str, Any]] = [
        {
            "name": "dashboard_loaded",
            "passed": response.status_code == 200,
            "status_code": response.status_code,
        }
    ]

    html = response.text

    required_markers = [
        "Materialization Execution Gate",
        "materializationExecutionGate",
        "materializationExecutionGateStatus",
        "materializationExecutionGateApproval",
        "materializationExecutionGateResultStatus",
        "materializationExecutionGateSafety",
        "materializationExecutionGateResult",
        "attemptMaterializationExecutionGate",
        "clearMaterializationExecutionGate",
        "renderMaterializationExecutionGate",
        "/materialization-execution-attempts",
        "materialization_execution_gate_blocked_no_write",
        "Gate only · no write capability",
        "execution_gate_only",
        "approval_checked",
        "approval_record_grants_execution: false",
        "materialization_execution_enabled: false",
        "materialization_execution_performed: false",
        "generated_files_written_to_disk: false",
        "filesystem_write_performed: false",
        "disk_write_performed: false",
        "runtime_server_started: false",
        "preview_server_started: false",
        "generated_code_execution_performed: false",
        "repair_applied: false",
        "restore_executed: false",
    ]

    checks.extend(_check_marker(html, marker) for marker in required_markers)

    preserved_markers = {
        "v61_persistent_approval_record_preserved": "Persistent Approval Record",
        "v60_approval_history_preserved": "Materialization Approval History",
        "v59_approval_workflow_preserved": "Materialization Approval Workflow",
        "v58_materialization_plan_preserved": "Approval-Gated Workspace Materialization Plan",
        "v57_static_preview_preserved": "Safe Static Preview Renderer",
        "v56_results_review_preserved": "App Build Results Review",
        "platform_function_builder_preserved": "Platform Function Builder",
        "platform_function_request_preserved": "Create Platform Function Request",
    }

    checks.extend(
        {"name": name, "passed": marker in html}
        for name, marker in preserved_markers.items()
    )

    safety_claims = [
        "does not write files",
        "execute generated code",
        "execution remains disabled",
        "No files were written",
    ]
    checks.append(
        {
            "name": "materialization_execution_gate_safety_claims",
            "passed": all(claim in html for claim in safety_claims),
        }
    )

    passed = all(check.get("passed") for check in checks)
    result = {
        "check": "browser_materialization_execution_gate_check",
        "checks": checks,
        "passed": passed,
        "success": passed,
    }

    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
