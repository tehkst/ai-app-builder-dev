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
        "Safe Static Preview Renderer",
        "safeStaticPreviewRenderer",
        "safeStaticPreviewStatus",
        "safeStaticPreviewSource",
        "safeStaticPreviewSafetyMode",
        "safeStaticPreviewSurface",
        "safeStaticPreviewResult",
        "renderSafeStaticPreview",
        "clearSafeStaticPreview",
        "sanitizeStaticPreviewContent",
        "isFrontendPreviewPath",
        "Sanitized DB preview only",
        "sanitized_db_preview_only",
        "DB-backed generated frontend files",
        "read-only sanitized static content only",
        "does not start a runtime server",
        "write generated files to disk",
        "execute generated code",
        "runtime_server_started: false",
        "preview_server_started: false",
        "generated_code_execution_performed: false",
        "disk_write_performed: false",
        "generated_files_written_to_disk: false",
        "repair_applied: false",
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
            "name": "v56_results_review_preserved",
            "passed": "App Build Results Review" in dashboard_text
            and "refreshAppBuildResultsReview" in dashboard_text
            and "appBuildReviewRuntimeServer" in dashboard_text,
        },
        {
            "name": "platform_function_builder_preserved",
            "passed": "Platform Function Builder" in dashboard_text
            and "Create Platform Function Request" in dashboard_text
            and "createSelfBuildModuleRequest" in dashboard_text,
        },
        {
            "name": "customer_app_builder_hidden",
            "passed": "New App Build Session" not in dashboard_text
            and "App Specification Builder" not in dashboard_text
            and "Run App Build" not in dashboard_text,
        },
        {
            "name": "static_preview_safety_claims",
            "passed": "No generated-code execution" not in dashboard_text
            and "runtime_server_started: false" in dashboard_text
            and "generated_code_execution_performed: false" in dashboard_text
            and "disk_write_performed: false" in dashboard_text
            and "repair_applied: false" in dashboard_text,
        },
    ]

    passed = all(check.get("passed") for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "check": "browser_safe_static_preview_renderer_check",
        "checks": checks,
    }


def main() -> int:
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
