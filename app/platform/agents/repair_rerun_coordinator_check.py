import json

import app.platform.services.repair_rerun_coordinator_service as rerun_service


WORKFLOW_RUN_ID = "v76-rerun-after-repair"
NO_REPAIR_WORKFLOW_RUN_ID = "v76-no-successful-repair"


class FakeSession:
    pass


def _history_with_success(workflow_run_id):
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": "repair_executor_v75_approval_gated_sandbox_only",
        "history": [
            {
                "workflow_run_id": workflow_run_id,
                "execution_status": "applied",
                "applied": True,
                "requested_by": "smoke_check",
                "created_at": "2026-06-08T00:00:00+00:00",
                "repair_kind": "source_code_repair",
                "failure_category": "syntax_error",
                "operation_count": 1,
                "operations": [
                    {
                        "operation": "replace_file_content",
                        "target_relative_path": "src/App.jsx",
                        "before_sha256": "before",
                        "after_sha256": "after",
                        "before_size_bytes": 10,
                        "after_size_bytes": 12,
                    }
                ],
            }
        ],
        "safety_flags": {
            "repair_executor_checked": True,
            "repair_applied": False,
            "sandbox_bound_repair_only": True,
        },
    }


def _history_without_success(workflow_run_id):
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": "repair_executor_v75_approval_gated_sandbox_only",
        "history": [],
        "safety_flags": {
            "repair_executor_checked": True,
            "repair_applied": False,
            "sandbox_bound_repair_only": True,
        },
    }


def _status_before(workflow_run_id):
    return {
        "success": True,
        "found": False,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "not_started",
        "safety_mode": "controlled_sandbox_runtime_v70_approved_sandbox_only",
        "process": None,
        "logs": {
            "success": True,
            "found": False,
            "workflow_run_id": workflow_run_id,
            "runtime_status": "not_started",
            "logs": {"stdout_line_count": 0, "stderr_line_count": 1},
        },
        "safety_flags": {"controlled_sandbox_runtime": True},
    }


def _logs_before(workflow_run_id):
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "exited",
        "safety_mode": "controlled_sandbox_runtime_v71_log_capture_only",
        "logs": {
            "stdout_tail": [],
            "stderr_tail": ["before error"],
            "stdout_line_count": 0,
            "stderr_line_count": 1,
        },
        "safety_flags": {"runtime_log_capture_enabled": True},
    }


def _start_runtime(db, workflow_run_id, perform_install=False):
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "running",
        "block_reason": None,
        "safety_mode": "controlled_sandbox_runtime_v70_approved_sandbox_only",
        "workspace_root": "/tmp/approved-sandbox/workspace",
        "working_directory": "/tmp/approved-sandbox/workspace",
        "process": {"pid": 1234, "started": True, "running": True, "port": 5173},
        "logs": {
            "success": True,
            "found": True,
            "workflow_run_id": workflow_run_id,
            "runtime_status": "running",
            "logs": {"stdout_line_count": 1, "stderr_line_count": 0},
        },
        "safety_flags": {
            "controlled_sandbox_runtime": True,
            "approval_gate_checked": True,
            "sandbox_boundary_checked": True,
            "runtime_execution_enabled": True,
            "runtime_server_started": True,
            "node_command_executed": True,
            "install_packages_performed": False,
            "restore_executed": False,
        },
    }


def _status_after(workflow_run_id):
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "running",
        "safety_mode": "controlled_sandbox_runtime_v70_approved_sandbox_only",
        "process": {"pid": 1234, "running": True},
        "logs": {
            "success": True,
            "found": True,
            "workflow_run_id": workflow_run_id,
            "runtime_status": "running",
            "logs": {"stdout_line_count": 1, "stderr_line_count": 0},
        },
        "safety_flags": {"controlled_sandbox_runtime": True},
    }


def _logs_after(workflow_run_id):
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "running",
        "safety_mode": "controlled_sandbox_runtime_v71_log_capture_only",
        "logs": {
            "stdout_tail": ["after ok"],
            "stderr_tail": [],
            "stdout_line_count": 1,
            "stderr_line_count": 0,
        },
        "safety_flags": {"runtime_log_capture_enabled": True},
    }


def _safe(result, *, rerun_started_expected):
    flags = result.get("safety_flags") or {}
    return (
        flags.get("repair_rerun_coordinator_checked") is True
        and flags.get("successful_repair_execution_required") is True
        and flags.get("rerun_started") is rerun_started_expected
        and flags.get("used_existing_controlled_runtime_path") is True
        and flags.get("auto_approval_performed") is False
        and flags.get("repair_plan_generated") is False
        and flags.get("repair_applied") is False
        and flags.get("restore_executed") is False
        and flags.get("module_rollout_performed") is False
        and flags.get("install_packages_performed") is False
        and flags.get("python_command_executed") is False
        and flags.get("preview_server_started") is False
    )


def run_check():
    rerun_service.reset_repair_rerun_history_for_check()

    original_history = rerun_service.get_repair_execution_history
    original_status = rerun_service.get_controlled_sandbox_runtime_status
    original_logs = rerun_service.get_controlled_sandbox_runtime_logs
    original_start = rerun_service.start_controlled_sandbox_runtime_for_workflow

    checks = {}
    samples = {}
    start_calls = []

    try:
        rerun_service.get_controlled_sandbox_runtime_status = _status_before
        rerun_service.get_controlled_sandbox_runtime_logs = _logs_before
        rerun_service.start_controlled_sandbox_runtime_for_workflow = _start_runtime
        rerun_service.get_repair_execution_history = _history_without_success

        blocked_result = rerun_service.rerun_after_successful_repair(
            db=FakeSession(),
            workflow_run_id=NO_REPAIR_WORKFLOW_RUN_ID,
            requested_by="smoke_check",
        )
        checks["blocked_without_successful_repair"] = blocked_result.get("blocked") is True and blocked_result.get("rerun_started") is False
        checks["blocked_has_before_metadata"] = blocked_result.get("before_runtime_status") is not None and blocked_result.get("before_runtime_logs") is not None
        checks["blocked_safe"] = _safe(blocked_result, rerun_started_expected=False)

        rerun_service.get_repair_execution_history = _history_with_success

        install_blocked_result = rerun_service.rerun_after_successful_repair(
            db=FakeSession(),
            workflow_run_id=WORKFLOW_RUN_ID,
            requested_by="smoke_check",
            perform_install=True,
        )
        checks["perform_install_blocked"] = install_blocked_result.get("blocked") is True and install_blocked_result.get("rerun_started") is False
        checks["perform_install_safe"] = _safe(install_blocked_result, rerun_started_expected=False)

        def _tracked_start(db, workflow_run_id, perform_install=False):
            start_calls.append({"workflow_run_id": workflow_run_id, "perform_install": perform_install})
            return _start_runtime(db, workflow_run_id, perform_install=perform_install)

        def _status_switch(workflow_run_id):
            return _status_after(workflow_run_id) if start_calls else _status_before(workflow_run_id)

        def _logs_switch(workflow_run_id):
            return _logs_after(workflow_run_id) if start_calls else _logs_before(workflow_run_id)

        rerun_service.start_controlled_sandbox_runtime_for_workflow = _tracked_start
        rerun_service.get_controlled_sandbox_runtime_status = _status_switch
        rerun_service.get_controlled_sandbox_runtime_logs = _logs_switch

        rerun_result = rerun_service.rerun_after_successful_repair(
            db=FakeSession(),
            workflow_run_id=WORKFLOW_RUN_ID,
            requested_by="smoke_check",
        )
        comparison = rerun_result.get("comparison") or {}
        checks["rerun_started_after_successful_repair"] = rerun_result.get("rerun_started") is True and rerun_result.get("blocked") is False
        checks["existing_runtime_path_called_once"] = start_calls == [{"workflow_run_id": WORKFLOW_RUN_ID, "perform_install": False}]
        checks["before_after_metadata_recorded"] = rerun_result.get("before_runtime_status") is not None and rerun_result.get("after_runtime_status") is not None
        checks["comparison_metadata_recorded"] = comparison.get("before_runtime_status") == "not_started" and comparison.get("after_runtime_status") == "running"
        checks["history_recorded"] = len(rerun_result.get("history") or []) == 1
        checks["rerun_safe"] = _safe(rerun_result, rerun_started_expected=True)

        history_result = rerun_service.get_repair_rerun_history(WORKFLOW_RUN_ID)
        checks["history_lookup_has_record"] = len(history_result.get("history") or []) == 1
        checks["history_lookup_safe"] = _safe(history_result, rerun_started_expected=False)

        samples = {
            "blocked_result": blocked_result,
            "install_blocked_result": install_blocked_result,
            "rerun_result": rerun_result,
            "history_result": history_result,
        }
    finally:
        rerun_service.get_repair_execution_history = original_history
        rerun_service.get_controlled_sandbox_runtime_status = original_status
        rerun_service.get_controlled_sandbox_runtime_logs = original_logs
        rerun_service.start_controlled_sandbox_runtime_for_workflow = original_start
        rerun_service.reset_repair_rerun_history_for_check()

    return {
        "check": "repair_rerun_coordinator_check",
        "passed": all(checks.values()),
        "checks": checks,
        "sample": samples,
    }


if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
