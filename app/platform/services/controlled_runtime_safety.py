from __future__ import annotations

from typing import Dict


CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE = "controlled_sandbox_runtime_v70_approved_sandbox_only"
CONTROLLED_SANDBOX_RUNTIME_LOG_SAFETY_MODE = "controlled_sandbox_runtime_v71_log_capture_only"


def safe_flags(
    *,
    runtime_started: bool = False,
    install_performed: bool = False,
    node_command_executed: bool = False,
) -> Dict[str, bool]:
    return {
        "controlled_sandbox_runtime": True,
        "approval_gate_checked": True,
        "sandbox_boundary_checked": True,
        "runtime_execution_enabled": runtime_started,
        "install_packages_performed": install_performed,
        "runtime_server_started": runtime_started,
        "preview_server_started": False,
        "generated_code_execution_performed": runtime_started,
        "node_command_executed": node_command_executed,
        "python_command_executed": False,
        "generated_files_written": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "repair_applied": False,
        "restore_executed": False,
    }


def log_safe_flags() -> Dict[str, bool]:
    flags = safe_flags()
    flags.update(
        {
            "runtime_log_capture_enabled": True,
            "ai_failure_analysis_performed": False,
            "repair_plan_generated": False,
            "module_rollout_performed": False,
        }
    )
    return flags
