import json
import shutil
import uuid
from pathlib import Path

from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.materialization_approval_record_service import (
    create_materialization_approval_record,
)
from app.platform.services.materialization_sandbox_writer_service import (
    APPROVED_SANDBOX_ROOT_BASE,
    write_generated_file_to_local_sandbox,
)


def run_check() -> dict:
    create_platform_tables()
    db = PlatformSessionLocal()

    run_token = uuid.uuid4().hex
    generated_file_id = f"v64-sandbox-writer-check-file-{run_token}"
    workspace_id = f"v64-sandbox-writer-check-workspace-{run_token}"
    target_relative_path = "frontend/index.html"
    expected_content = "<html><body>V64 sandbox writer check</body></html>"

    sandbox_root = APPROVED_SANDBOX_ROOT_BASE / workspace_id
    shutil.rmtree(sandbox_root, ignore_errors=True)

    try:
        existing = (
            db.query(PlatformGeneratedFile)
            .filter(PlatformGeneratedFile.generated_file_id == generated_file_id)
            .first()
        )
        if existing:
            db.delete(existing)
            db.commit()

        generated_file = PlatformGeneratedFile(
            generated_file_id=generated_file_id,
            workflow_run_id="v64-sandbox-writer-check-run",
            workspace_id=workspace_id,
            project_id="v64-sandbox-writer-check-project",
            source_step_id="v64-check-step",
            source_agent_id="v64-check-agent",
            path=target_relative_path,
            language="html",
            purpose="V64 sandbox writer smoke check",
            content_preview=expected_content,
            content_hash="v64-check-content-hash",
            write_status="persisted_preview",
            rollback_status="not_required",
            metadata_json="{}",
        )
        db.add(generated_file)
        db.commit()

        blocked_without_approval = write_generated_file_to_local_sandbox(
            db,
            generated_file_id=generated_file_id,
        )

        approval = create_materialization_approval_record(
            db,
            generated_file_id=generated_file_id,
            approved_by="v64_sandbox_writer_check",
            approval_reason="Required for V64 sandbox writer smoke check.",
        )

        written = write_generated_file_to_local_sandbox(
            db,
            generated_file_id=generated_file_id,
        )

        target_path = Path(written.get("target_path") or "")
        target_exists = target_path.exists()
        target_content = target_path.read_text(encoding="utf-8") if target_exists else ""

        target_inside_sandbox = False
        try:
            target_path.resolve(strict=False).relative_to(sandbox_root.resolve(strict=False))
            target_inside_sandbox = True
        except ValueError:
            target_inside_sandbox = False

        checks = {
            "blocked_without_approval": blocked_without_approval.get("write_status") == "blocked",
            "approval_created": approval.get("record_created") is True,
            "write_status_written": written.get("write_status") == "written_to_local_sandbox",
            "sandbox_write_enabled": written.get("sandbox_write_enabled") is True,
            "filesystem_write_performed": written.get("filesystem_write_performed") is True,
            "disk_write_performed": written.get("disk_write_performed") is True,
            "generated_files_written_to_disk": written.get("generated_files_written_to_disk") is True,
            "target_exists": target_exists,
            "target_inside_sandbox": target_inside_sandbox,
            "target_content_matches": target_content == expected_content,
            "no_generated_code_execution": written.get("generated_code_execution_performed") is False,
            "no_runtime_server": written.get("runtime_server_started") is False,
            "no_preview_server": written.get("preview_server_started") is False,
            "no_repair_applied": written.get("repair_applied") is False,
            "no_restore_executed": written.get("restore_executed") is False,
        }

        return {
            "check": "materialization_sandbox_writer_check",
            "passed": all(checks.values()),
            "checks": checks,
            "samples": {
                "blocked_without_approval": blocked_without_approval,
                "approval": approval,
                "written": written,
            },
        }
    finally:
        shutil.rmtree(sandbox_root, ignore_errors=True)
        db.close()


if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
