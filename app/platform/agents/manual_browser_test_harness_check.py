import json
import shutil
import uuid
from pathlib import Path

from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.manual_browser_test_harness_service import (
    prepare_manual_browser_test_harness,
)
from app.platform.services.materialization_approval_record_service import (
    create_materialization_approval_record,
)
from app.platform.services.materialization_sandbox_writer_service import (
    APPROVED_SANDBOX_ROOT_BASE,
    write_generated_file_to_local_sandbox,
)


def _create_generated_file(
    db,
    generated_file_id: str,
    workspace_id: str,
    path: str,
    language: str,
    content: str,
) -> PlatformGeneratedFile:
    generated_file = PlatformGeneratedFile(
        generated_file_id=generated_file_id,
        workflow_run_id="v65-manual-browser-harness-check-run",
        workspace_id=workspace_id,
        project_id="v65-manual-browser-harness-check-project",
        source_step_id="v65-check-step",
        source_agent_id="v65-check-agent",
        path=path,
        language=language,
        purpose="V65 manual browser test harness smoke check",
        content_preview=content,
        content_hash=f"v65-check-content-hash-{generated_file_id}",
        write_status="persisted_preview",
        rollback_status="not_required",
        metadata_json="{}",
    )
    db.add(generated_file)
    db.commit()
    return generated_file


def run_check() -> dict:
    create_platform_tables()
    db = PlatformSessionLocal()

    run_token = uuid.uuid4().hex
    workspace_id = f"v65-manual-browser-harness-workspace-{run_token}"
    html_generated_file_id = f"v65-manual-browser-harness-html-{run_token}"
    py_generated_file_id = f"v65-manual-browser-harness-py-{run_token}"

    sandbox_root = APPROVED_SANDBOX_ROOT_BASE / workspace_id
    shutil.rmtree(sandbox_root, ignore_errors=True)

    try:
        _create_generated_file(
            db,
            generated_file_id=html_generated_file_id,
            workspace_id=workspace_id,
            path="frontend/index.html",
            language="html",
            content="<html><body><h1>V65 manual browser harness</h1></body></html>",
        )
        _create_generated_file(
            db,
            generated_file_id=py_generated_file_id,
            workspace_id=workspace_id,
            path="backend/app/main.py",
            language="python",
            content="print('blocked by V65 harness')",
        )

        missing_before_write = prepare_manual_browser_test_harness(
            db,
            generated_file_id=html_generated_file_id,
        )

        create_materialization_approval_record(
            db,
            generated_file_id=html_generated_file_id,
            approved_by="v65_manual_browser_test_harness_check",
            approval_reason="Required to write the V65 HTML smoke-check file into the sandbox.",
        )

        written = write_generated_file_to_local_sandbox(
            db,
            generated_file_id=html_generated_file_id,
        )

        ready = prepare_manual_browser_test_harness(
            db,
            generated_file_id=html_generated_file_id,
        )

        blocked_backend = prepare_manual_browser_test_harness(
            db,
            generated_file_id=py_generated_file_id,
        )

        target_path = Path(ready.get("target_path") or "")
        target_inside_sandbox = False
        try:
            target_path.resolve(strict=False).relative_to(sandbox_root.resolve(strict=False))
            target_inside_sandbox = True
        except ValueError:
            target_inside_sandbox = False

        checks = {
            "missing_before_write_blocked": missing_before_write.get("harness_status") == "blocked",
            "missing_before_write_no_server": missing_before_write.get("preview_server_started") is False,
            "sandbox_write_completed": written.get("write_status") == "written_to_local_sandbox",
            "ready_for_manual_open": ready.get("harness_status") == "ready_for_manual_open",
            "manual_test_enabled": ready.get("manual_test_enabled") is True,
            "manual_browser_url_file_scheme": str(ready.get("manual_browser_url") or "").startswith("file://"),
            "target_inside_sandbox": target_inside_sandbox,
            "backend_file_blocked": blocked_backend.get("harness_status") == "blocked",
            "backend_reason_static_only": "static HTML" in (blocked_backend.get("block_reason") or ""),
            "no_generated_code_execution": ready.get("generated_code_execution_performed") is False,
            "no_runtime_server": ready.get("runtime_server_started") is False,
            "no_preview_server": ready.get("preview_server_started") is False,
            "no_server_start": ready.get("server_start_performed") is False,
            "no_npm_install": ready.get("npm_install_performed") is False,
            "no_node_command": ready.get("node_command_executed") is False,
            "no_python_command": ready.get("python_command_executed") is False,
            "no_repair_applied": ready.get("repair_applied") is False,
            "no_restore_executed": ready.get("restore_executed") is False,
        }

        return {
            "check": "manual_browser_test_harness_check",
            "passed": all(checks.values()),
            "checks": checks,
            "samples": {
                "missing_before_write": missing_before_write,
                "written": written,
                "ready": ready,
                "blocked_backend": blocked_backend,
            },
        }
    finally:
        shutil.rmtree(sandbox_root, ignore_errors=True)
        db.close()


if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
