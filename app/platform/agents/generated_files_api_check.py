from __future__ import annotations

import json
from typing import Any, Dict

from fastapi.testclient import TestClient

from app.main import app
from app.platform.api.security import require_platform_admin


def run_generated_files_api_check() -> Dict[str, Any]:
    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)

    checks = []

    run_response = client.post(
        "/platform/app-build/run",
        json={
            "app_request": "Build me a simple todo app with login and tasks",
            "real_bridge": True,
        },
    )
    run_data = run_response.json()
    workflow_run_id = (run_data.get("summary") or {}).get("workflow_run_id")

    run_passed = (
        run_response.status_code == 200
        and run_data.get("success") is True
        and run_data.get("status") == "completed"
        and bool(workflow_run_id)
    )
    checks.append(
        {
            "name": "run_app_build",
            "passed": run_passed,
            "status_code": run_response.status_code,
            "workflow_run_id": workflow_run_id,
        }
    )

    generated_files_passed = False
    generated_files_status_code = None
    generated_file_count = 0
    first_file = {}

    if workflow_run_id:
        generated_files_response = client.get(
            f"/platform/app-build/runs/{workflow_run_id}/generated-files"
        )
        generated_files_status_code = generated_files_response.status_code
        generated_files_data = generated_files_response.json()
        generated_files = generated_files_data.get("generated_files") or []
        generated_file_count = generated_files_data.get("generated_file_count") or 0
        first_file = generated_files[0] if generated_files else {}

        required_file_fields = {
            "path",
            "language",
            "purpose",
            "content_preview",
            "write_status",
            "source_step_id",
            "source_agent_id",
        }

        generated_files_passed = (
            generated_files_response.status_code == 200
            and generated_files_data.get("success") is True
            and generated_files_data.get("found") is True
            and generated_files_data.get("workflow_run_id") == workflow_run_id
            and generated_file_count == len(generated_files)
            and generated_file_count >= 1
            and required_file_fields.issubset(set(first_file.keys()))
            and first_file.get("write_status") == "preview_only"
        )

    checks.append(
        {
            "name": "generated_files_endpoint",
            "passed": generated_files_passed,
            "status_code": generated_files_status_code,
            "workflow_run_id": workflow_run_id,
            "generated_file_count": generated_file_count,
            "first_file": first_file,
        }
    )

    passed = all(check["passed"] for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "checks": checks,
        "workflow_run_id": workflow_run_id,
        "generated_file_count": generated_file_count,
    }


def main() -> None:
    result = run_generated_files_api_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
