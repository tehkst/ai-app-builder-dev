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
        "Manual Browser Test Harness",
        "manualBrowserTestHarnessPanel",
        "manualBrowserTestHarnessStatus",
        "manualBrowserTestHarnessSource",
        "manualBrowserTestHarnessSafety",
        "manualBrowserTestHarnessInstructions",
        "manualBrowserTestHarnessResult",
        "prepareManualBrowserTestHarness",
        "clearManualBrowserTestHarness",
        "Static HTML manual-open only",
        "static HTML files only",
        "It does not start a server",
        "run package commands",
        "execute generated backend code",
        "apply repairs",
        "execute restores",
        "manual_open_required",
        "manual_test_enabled",
        "runtime_server_started",
        "preview_server_started",
        "generated_code_execution_performed",
        "filesystem_write_performed",
        "disk_write_performed",
        "generated_files_written_to_disk",
        "repair_applied",
        "restore_executed",
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
            "name": "v65_ui_preserved",
            "passed": "prepareManualBrowserTestHarness" in dashboard_text
            and "manualBrowserTestHarnessPanel" in dashboard_text,
        },
        {
            "name": "v64_sandbox_writer_behavior_preserved",
            "passed": "local sandbox" in dashboard_text
            or "sandbox-written" in dashboard_text,
        },
        {
            "name": "v57_static_preview_preserved",
            "passed": "safeStaticPreviewRenderer" in dashboard_text
            and "renderSafeStaticPreview" in dashboard_text,
        },
        {
            "name": "v56_results_review_preserved",
            "passed": "appBuildResultsReview" in dashboard_text
            and "refreshAppBuildResultsReview" in dashboard_text,
        },
        {
            "name": "v55_spec_builder_preserved",
            "passed": "appSpecificationBuilder" in dashboard_text
            and "generateAppSpecificationPrompt" in dashboard_text,
        },
        {
            "name": "v54_launcher_preserved",
            "passed": "newAppBuildSessionLauncher" in dashboard_text
            and "launchNewAppBuildSession" in dashboard_text,
        },
        {
            "name": "manual_browser_harness_panel_safety_claims",
            "passed": "does not start a server" in dashboard_text
            and "run package commands" in dashboard_text
            and "execute generated backend code" in dashboard_text
            and "apply repairs" in dashboard_text
            and "execute restores" in dashboard_text,
        },
    ]

    passed = all(check.get("passed") for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "check": "browser_manual_test_harness_panel_check",
        "checks": checks,
    }


def main() -> int:
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
