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
        "Browser One-Click Repair Flow",
        "one-click-repair-flow",
        "oneClickRepairStatus",
        "oneClickRepairApprovalRequired",
        "oneClickRepairExecutionMode",
        "oneClickRepairResult",
        "createOneClickRepairProposal",
        "clearOneClickRepairProposal",
        "Create Repair Proposal",
        "Clear Repair Proposal",
        "proposal_only",
        "approval_required_before_execution: true",
        "repair_actions_generated: false",
        "repair_actions_applied: false",
        "db_content_mutation_performed: false",
        "disk_write_performed: false",
        "generated_code_execution_performed: false",
        "preview_server_started: false",
        "runtime_execution_enabled: false",
        "This milestone creates a proposal only",
        "It does not apply repairs, mutate workspace content, write files, start a runtime server, or execute generated code",
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
            "name": "proposal_only_no_execution_claim",
            "passed": "proposal_only" in dashboard_text
            and "approval_required_before_execution: true" in dashboard_text
            and "repair_actions_applied: false" in dashboard_text
            and "db_content_mutation_performed: false" in dashboard_text
            and "generated_code_execution_performed: false" in dashboard_text,
        },
    ]

    passed = all(check.get("passed") for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "check": "browser_one_click_repair_flow_check",
        "checks": checks,
    }


def main() -> int:
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
