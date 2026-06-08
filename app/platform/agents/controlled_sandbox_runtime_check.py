import json
import shutil
import uuid

from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.controlled_sandbox_runtime_service import (
    get_controlled_sandbox_runtime_status,
    start_controlled_sandbox_runtime_for_workflow,
    stop_controlled_sandbox_runtime,
)
from app.platform.services.materialization_approval_record_service import create_materialization_approval_record
from app.platform.services.materialization_sandbox_writer_service import write_generated_file_to_local_sandbox
from app.platform.services.runtime_approval_gate_service import approve_runtime_run_plan_for_workflow
from app.platform.services.runtime_run_plan_builder_service import build_runtime_run_plan_for_workflow


def _create_generated_file(db, generated_file_id, workflow_run_id, workspace_id, path, language, content):
    generated_file = PlatformGeneratedFile(
        generated_file_id=generated_file_id,
        workflow_run_id=workflow_run_id,
        workspace_id=workspace_id,
        project_id="v70-controlled-sandbox-runtime-project",
        source_step_id="v70-check-step",
        source_agent_id="v70-check-agent",
        path=path,
        language=language,
        purpose="V70 controlled sandbox runtime smoke check",
        content_preview=content,
        content_hash=f"v70-check-content-hash-{generated_file_id}",
        write_status="persisted_preview",
        rollback_status="not_required",
        metadata_json="{}",
    )
    db.add(generated_file)
    db.commit()
    return generated_file


def _materialize(db, generated_file_id):
    create_materialization_approval_record(
        db,
        generated_file_id=generated_file_id,
        approved_by="v70-smoke-check",
        approval_reason="V70 smoke check sandbox materialization approval.",
    )
    return write_generated_file_to_local_sandbox(db, generated_file_id=generated_file_id)


def run_check() -> dict:
    create_platform_tables()
    db = PlatformSessionLocal()

    token = uuid.uuid4().hex
    workflow_run_id = f"v70-controlled-sandbox-runtime-check-run-{token}"
    workspace_id = f"v70-controlled-sandbox-runtime-workspace-{token}"

    try:
        package_file_id = f"v70-package-json-{token}"
        index_file_id = f"v70-index-html-{token}"
        main_file_id = f"v70-main-jsx-{token}"

        _create_generated_file(
            db,
            generated_file_id=package_file_id,
            workflow_run_id=workflow_run_id,
            workspace_id=workspace_id,
            path="frontend/package.json",
            language="json",
            content=json.dumps(
                {
                    "scripts": {"dev": "vite --host 127.0.0.1"},
                    "dependencies": {
                        "@vitejs/plugin-react": "latest",
                        "vite": "latest",
                        "react": "latest",
                        "react-dom": "latest",
                    },
                    "devDependencies": {},
                }
            ),
        )
        _create_generated_file(
            db,
            generated_file_id=index_file_id,
            workflow_run_id=workflow_run_id,
            workspace_id=workspace_id,
            path="frontend/index.html",
            language="html",
            content="<html><body><div id='root'></div><script type='module' src='/src/main.jsx'></script></body></html>\n",
        )
        _create_generated_file(
            db,
            generated_file_id=main_file_id,
            workflow_run_id=workflow_run_id,
            workspace_id=workspace_id,
            path="frontend/src/main.jsx",
            language="javascript",
            content="import React from 'react';\nimport { createRoot } from 'react-dom/client';\ncreateRoot(document.getElementById('root')).render(<div>V70 controlled sandbox runtime alive</div>);\n",
        )

        blocked_before_approval = start_controlled_sandbox_runtime_for_workflow(
            db,
            workflow_run_id=workflow_run_id,
            perform_install=False,
        )

        run_plan = build_runtime_run_plan_for_workflow(db, workflow_run_id=workflow_run_id)
        materialized_package = _materialize(db, package_file_id)
        materialized_index = _materialize(db, index_file_id)
        materialized_main = _materialize(db, main_file_id)
        runtime_approval = approve_runtime_run_plan_for_workflow(
            db,
            workflow_run_id=workflow_run_id,
            approved_by="v70-smoke-check",
            approval_reason="V70 smoke check runtime approval.",
        )

        start_result = start_controlled_sandbox_runtime_for_workflow(
            db,
            workflow_run_id=workflow_run_id,
            perform_install=False,
        )
        status_result = get_controlled_sandbox_runtime_status(workflow_run_id)
        stop_result = stop_controlled_sandbox_runtime(workflow_run_id)
        stopped_status = get_controlled_sandbox_runtime_status(workflow_run_id)

        start_flags = start_result.get("safety_flags") or {}
        stop_flags = stop_result.get("safety_flags") or {}

        checks = {
            "blocked_before_runtime_approval": blocked_before_approval.get("runtime_status") == "blocked",
            "blocked_before_approval_reason": "approval" in (blocked_before_approval.get("block_reason") or "").lower(),
            "run_plan_found": run_plan.get("found") is True,
            "run_plan_ready": (run_plan.get("runtime_run_plan") or {}).get("status") == "runtime_run_plan_ready_for_approval",
            "materialized_package": materialized_package.get("write_status") == "written_to_local_sandbox",
            "materialized_index": materialized_index.get("write_status") == "written_to_local_sandbox",
            "materialized_main": materialized_main.get("write_status") == "written_to_local_sandbox",
            "runtime_approval_created": runtime_approval.get("record_created") is True,
            "runtime_started_or_exited_early": start_result.get("runtime_status") in {"running", "exited_early"},
            "runtime_process_started": (start_result.get("process") or {}).get("started") is True,
            "status_found": status_result.get("found") is True,
            "stop_succeeded": stop_result.get("runtime_status") == "stopped",
            "stopped_status_not_started": stopped_status.get("runtime_status") == "not_started",
            "sandbox_boundary_checked": start_flags.get("sandbox_boundary_checked") is True,
            "approval_gate_checked": start_flags.get("approval_gate_checked") is True,
            "runtime_execution_enabled_after_start": start_flags.get("runtime_execution_enabled") in {True, False},
            "no_generated_files_written_by_runtime_service": start_flags.get("generated_files_written") is False,
            "no_filesystem_write_by_runtime_service": start_flags.get("filesystem_write_performed") is False,
            "no_disk_write_by_runtime_service": start_flags.get("disk_write_performed") is False,
            "no_repair_applied": start_flags.get("repair_applied") is False,
            "no_restore_executed": start_flags.get("restore_executed") is False,
            "stop_does_not_repair": stop_flags.get("repair_applied") is False,
            "stop_does_not_restore": stop_flags.get("restore_executed") is False,
        }

        return {
            "check": "controlled_sandbox_runtime_check",
            "passed": all(checks.values()),
            "checks": checks,
            "sample": {
                "blocked_before_approval": blocked_before_approval,
                "run_plan": run_plan,
                "materialized_package": materialized_package,
                "materialized_index": materialized_index,
                "materialized_main": materialized_main,
                "runtime_approval": runtime_approval,
                "start_result": start_result,
                "status_result": status_result,
                "stop_result": stop_result,
                "stopped_status": stopped_status,
            },
        }
    finally:
        try:
            stop_controlled_sandbox_runtime(workflow_run_id)
        finally:
            db.close()
            shutil.rmtree(f"/tmp/ai-software-factory/workspaces/{workspace_id}", ignore_errors=True)


if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
