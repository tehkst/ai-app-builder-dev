# Split from the legacy module to keep each Python file under 200 lines.
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
