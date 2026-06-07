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
        "New App Build Session",
        "newAppBuildSessionLauncher",
        "newAppProjectName",
        "newAppType",
        "newAppIdea",
        "newAppRealBridge",
        "launchNewAppBuildSession",
        "buildNewAppSessionRequest",
        "updateNewAppSessionMetadata",
        "Start App Build Session",
        "newAppSessionProject",
        "newAppSessionType",
        "newAppSessionRunId",
        "newAppSessionSafety",
        "DB-preview-only generation",
        "does not write generated files to disk or execute generated code",
    ]

    marker_checks = [
        {
            "name": f"marker_present::{marker}",
            "passed": marker in dashboard_text,
        }
        for marker in required_markers
    ]

    checks = [
        {
            "name": "dashboard_loaded",
            "passed": response.status_code == 200,
            "status_code": response.status_code,
        },
        *marker_checks,
        {
            "name": "safety_claims_preserved",
            "passed": "does not write generated files to disk" in dashboard_text
            and "execute generated code" in dashboard_text
            and "DB preview only" in dashboard_text,
        },
    ]

    passed = all(check.get("passed") for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "check": "browser_app_build_session_launcher_check",
        "checks": checks,
    }


def main() -> int:
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
