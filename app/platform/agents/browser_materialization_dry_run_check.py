from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.platform.api import app_build_routes
from app.platform.api.security import require_platform_admin


def _override_admin():
    return True


def main() -> int:
    app = FastAPI()
    app.include_router(app_build_routes.router)
    app.dependency_overrides[require_platform_admin] = _override_admin

    client = TestClient(app)
    response = client.get("/platform/app-build/dashboard")

    if response.status_code != 200:
        print("V63 browser materialization dry run check failed: dashboard did not load")
        print(response.status_code)
        print(response.text[:500])
        return 1

    html = response.text

    required_markers = [
        "Safe Workspace Materialization Dry Run",
        "safeWorkspaceMaterializationDryRun",
        "materializationDryRunStatus",
        "materializationDryRunFileCount",
        "materializationDryRunApproval",
        "materializationDryRunSafety",
        "materializationDryRunPaths",
        "materializationDryRunResult",
        "buildSafeWorkspaceMaterializationDryRun",
        "clearSafeWorkspaceMaterializationDryRun",
        "renderSafeWorkspaceMaterializationDryRun",
        "/materialization-dry-runs",
        "safe_workspace_materialization_dry_run_only",
        "Dry run only · no writes",
        "dry_run_only",
        "would_write_file_count",
        "dry_run_files",
        "write_mode",
        "db_preview_only",
        "materialization_execution_enabled",
        "materialization_execution_performed",
        "generated_files_written_to_disk",
        "filesystem_write_performed",
        "disk_write_performed",
        "runtime_server_started",
        "preview_server_started",
        "generated_code_execution_performed",
        "repair_applied",
        "restore_executed",
        "No files were written",
        "No files will be written",
    ]

    preserved_markers = [
        "Materialization Execution Gate",
        "Persistent Approval Record",
        "Materialization Approval History",
        "Materialization Approval Workflow",
        "Approval-Gated Workspace Materialization Plan",
        "Safe Static Preview Renderer",
        "App Build Results Review",
        "Platform Function Builder",
        "Create Platform Function Request",
    ]

    missing = [marker for marker in required_markers + preserved_markers if marker not in html]
    if missing:
        print("V63 browser materialization dry run check failed: missing markers")
        for marker in missing:
            print("-", marker)
        return 1

    print("V63 browser materialization dry run check passed")
    print("Verified dry-run-only materialization UI markers")
    print("Verified materialization, preview, review, and platform function markers")
    print("Verified no-write/no-execution/no-server/no-repair/no-restore safety markers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
