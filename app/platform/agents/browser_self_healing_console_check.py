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
        "Browser Self-Healing Console",
        "self-healing-console",
        "selfHealingStatus",
        "selfHealingIssueCount",
        "selfHealingRepairMode",
        "selfHealingDiagnosticPills",
        "selfHealingResult",
        "analyzeCurrentWorkspaceForHealing",
        "clearSelfHealingConsole",
        "diagnostic_only",
        "Analyze Current Workspace",
        "Clear Self-Healing Console",
        "This milestone only analyzes visible workflow/file state",
        "It does not apply repairs, write files, start a preview server, or execute generated code",
        "repair_actions_generated: false",
        "repair_actions_applied: false",
        "disk_write_performed: false",
        "generated_code_execution_performed: false",
        "preview_server_started: false",
        "runtime_execution_enabled: false",
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
            "name": "diagnostic_only_no_repair_claim",
            "passed": "does not apply repairs" in dashboard_text.lower()
            and "diagnostic_only" in dashboard_text
            and "repair_actions_applied: false" in dashboard_text,
        },
    ]

    passed = all(check.get("passed") for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "check": "browser_self_healing_console_check",
        "checks": checks,
    }


def main() -> int:
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
