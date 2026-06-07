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
        "App Specification Builder",
        "appSpecificationBuilder",
        "specAppName",
        "specTargetUsers",
        "specCoreFeatures",
        "specNeedsAuth",
        "specNeedsPayments",
        "specNeedsAdmin",
        "specDatabaseEntities",
        "generateAppSpecificationPrompt",
        "useGeneratedAppSpecificationForSession",
        "Generate App Specification",
        "Use Spec For App Build Session",
        "appSpecificationPreview",
        "appSpecStatus",
        "appSpecSafety",
        "Prompt only",
        "DB-preview-only app-build workflow",
        "Do not write generated files to disk",
        "Do not execute generated code",
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
            "name": "v54_launcher_preserved",
            "passed": "New App Build Session" in dashboard_text
            and "launchNewAppBuildSession" in dashboard_text
            and "newAppIdea" in dashboard_text,
        },
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
        "check": "browser_app_spec_builder_check",
        "checks": checks,
    }


def main() -> int:
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
