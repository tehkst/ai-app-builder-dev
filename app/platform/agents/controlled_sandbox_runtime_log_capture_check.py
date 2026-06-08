import json
import shutil
import time
import uuid

from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.controlled_sandbox_runtime_service import (
    get_controlled_sandbox_runtime_logs,
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
        project_id="v71-controlled-runtime-log-capture-project",
        source_step_id="v71-check-step",
        source_agent_id="v71-check-agent",
        path=path,
        language=language,
        purpose="V71 controlled sandbox runtime log capture smoke check",
        content_preview=content,
        content_hash=f"v71-check-content-hash-{generated_file_id}",
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
        approved_by="v71-smoke-check",
        approval_reason="V71 smoke check sandbox materialization approval.",
    )
    return write_generated_file_to_local_sandbox(db, generated_file_id=generated_file_id)


def _contains(lines, needle):
    return any(needle in line for line in lines or [])


def run_check() -> dict:
    create_platform_tables()
    db = PlatformSessionLocal()

    token = uuid.uuid4().hex
    workflow_run_id = f"v71-controlled-runtime-log-capture-check-run-{token}"
    workspace_id = f"v71-controlled-runtime-log-capture-workspace-{token}"

    try:
        package_file_id = f"v71-package-json-{token}"
        index_file_id = f"v71-index-html-{token}"
        main_file_id = f"v71-main-jsx-{token}"

        _create_generated_file(
            db,
            generated_file_id=package_file_id,
            workflow_run_id=workflow_run_id,
            workspace_id=workspace_id,
            path="frontend/package.json",
            language="json",
            content=json.dumps(
                {
                    "scripts": {"dev": "node src/main.jsx"},
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
            content="<html><body><div id='root'>V71 log capture fixture</div><script type='module' src='/src/main.jsx'></script></body></html>\n",
        )
        _create_generated_file(
            db,
            generated_file_id=main_file_id,
            workflow_run_id=workflow_run_id,
            workspace_id=workspace_id,
            path="frontend/src/main.jsx",
            language="javascript",
            content=(
                "console.log('V71_STDOUT_READY');\n"
                "console.error('V71_STDERR_READY');\n"
                "setInterval(() => console.log('V71_STDOUT_TICK'), 250);\n"
            ),
        )

        run_plan = build_runtime_run_plan_for_workflow(db, workflow_run_id=workflow_run_id)
        materialized_package = _materialize(db, package_file_id)
        materialized_index = _materialize(db, index_file_id)
        materialized_main = _materialize(db, main_file_id)
        runtime_approval = approve_runtime_run_plan_for_workflow(
            db,
            workflow_run_id=workflow_run_id,
            approved_by="v71-smoke-check",
            approval_reason="V71 smoke check runtime approval.",
        )

        start_result = start_controlled_sandbox_runtime_for_workflow(
            db,
            workflow_run_id=workflow_run_id,
            perform_install=False,
        )
        time.sleep(1.5)
        logs_while_running = get_controlled_sandbox_runtime_logs(workflow_run_id)
        status_result = get_controlled_sandbox_runtime_status(workflow_run_id)
        stop_result = stop_controlled_sandbox_runtime(workflow_run_id)
        time.sleep(0.2)
        logs_after_stop = get_controlled_sandbox_runtime_logs(workflow_run_id)

        running_logs = logs_while_running.get("logs") or {}
        stopped_logs = logs_after_stop.get("logs") or {}
        stdout_tail = running_logs.get("stdout_tail") or []
        stderr_tail = running_logs.get("stderr_tail") or []
        stopped_stdout_tail = stopped_logs.get("stdout_tail") or []
        stopped_stderr_tail = stopped_logs.get("stderr_tail") or []
        log_flags = logs_while_running.get("safety_flags") or {}
        stop_flags = stop_result.get("safety_flags") or {}

        checks = {
            "run_plan_found": run_plan.get("found") is True,
            "run_plan_ready": (run_plan.get("runtime_run_plan") or {}).get("status") == "runtime_run_plan_ready_for_approval",
            "materialized_package": materialized_package.get("write_status") == "written_to_local_sandbox",
            "materialized_index": materialized_index.get("write_status") == "written_to_local_sandbox",
            "materialized_main": materialized_main.get("write_status") == "written_to_local_sandbox",
            "runtime_approval_created": runtime_approval.get("record_created") is True,
            "runtime_process_started": (start_result.get("process") or {}).get("started") is True,
            "logs_found_while_running": logs_while_running.get("found") is True,
            "stdout_ready_captured": _contains(stdout_tail, "V71_STDOUT_READY"),
            "stderr_ready_captured": _contains(stderr_tail, "V71_STDERR_READY"),
            "stdout_line_count_positive": (running_logs.get("stdout_line_count") or 0) > 0,
            "stderr_line_count_positive": (running_logs.get("stderr_line_count") or 0) > 0,
            "status_found": status_result.get("found") is True,
            "stop_succeeded": stop_result.get("runtime_status") == "stopped",
            "logs_found_after_stop": logs_after_stop.get("found") is True,
            "stdout_preserved_after_stop": _contains(stopped_stdout_tail, "V71_STDOUT_READY"),
            "stderr_preserved_after_stop": _contains(stopped_stderr_tail, "V71_STDERR_READY"),
            "exit_code_captured_after_stop": (logs_after_stop.get("process") or {}).get("exit_code") is not None,
            "log_capture_enabled": log_flags.get("runtime_log_capture_enabled") is True,
            "no_ai_failure_analysis": log_flags.get("ai_failure_analysis_performed") is False,
            "no_repair_plan_generated": log_flags.get("repair_plan_generated") is False,
            "no_repair_applied": log_flags.get("repair_applied") is False and stop_flags.get("repair_applied") is False,
            "no_restore_executed": log_flags.get("restore_executed") is False and stop_flags.get("restore_executed") is False,
            "no_module_rollout": log_flags.get("module_rollout_performed") is False,
        }

        return {
            "check": "controlled_sandbox_runtime_log_capture_check",
            "passed": all(checks.values()),
            "checks": checks,
            "sample": {
                "run_plan": run_plan,
                "materialized_package": materialized_package,
                "materialized_index": materialized_index,
                "materialized_main": materialized_main,
                "runtime_approval": runtime_approval,
                "start_result": start_result,
                "logs_while_running": logs_while_running,
                "status_result": status_result,
                "stop_result": stop_result,
                "logs_after_stop": logs_after_stop,
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
