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
        "Browser Preview / Run Panel",
        "preview-panel",
        "browserPreviewStatus",
        "browserPreviewSource",
        "browserPreviewExecutionMode",
        "browserPreviewFrame",
        "browserPreviewResult",
        "prepareSafeBrowserPreview",
        "clearSafeBrowserPreview",
        "safe_shell_only",
        "Runtime execution is disabled",
        "No preview server is started",
        "no generated code is executed",
        "preview_server_started: false",
        "runtime_execution_enabled: false",
        "generated_code_execution_performed: false",
        "disk_write_performed: false",
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
            "name": "no_real_preview_server_claim",
            "passed": "no preview server is started" in dashboard_text.lower()
            and "runtime execution is disabled" in dashboard_text.lower()
            and "runtime preview is not enabled yet" in dashboard_text.lower(),
        },
    ]

    passed = all(check.get("passed") for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "check": "browser_preview_run_panel_check",
        "checks": checks,
    }


def main() -> int:
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
