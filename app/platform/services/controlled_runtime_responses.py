from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from app.platform.services.controlled_runtime_logs import runtime_log_snapshot
from app.platform.services.controlled_runtime_safety import CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE, safe_flags


def blocked_runtime_response(
    workflow_run_id: str,
    block_reason: str,
    *,
    run_plan_result: Optional[Dict[str, Any]] = None,
    approval_result: Optional[Dict[str, Any]] = None,
    workspace_root: Optional[str] = None,
    working_directory: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "success": True,
        "found": bool(run_plan_result and run_plan_result.get("found")),
        "workflow_run_id": workflow_run_id,
        "runtime_status": "blocked",
        "block_reason": block_reason,
        "safety_mode": CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE,
        "workspace_root": workspace_root,
        "working_directory": working_directory,
        "run_plan": (run_plan_result or {}).get("runtime_run_plan"),
        "runtime_approval": (approval_result or {}).get("approval_record"),
        "process": None,
        "logs": runtime_log_snapshot(workflow_run_id),
        "safety_flags": safe_flags(),
    }


def already_running_response(workflow_run_id: str, process: subprocess.Popen) -> Dict[str, Any]:
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "already_running",
        "block_reason": None,
        "safety_mode": CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE,
        "process": {"pid": process.pid, "poll": process.poll(), "started": True, "already_running": True},
        "logs": runtime_log_snapshot(workflow_run_id),
        "safety_flags": safe_flags(runtime_started=True, node_command_executed=True),
    }


def install_failed_response(
    workflow_run_id: str,
    workspace_root: Path,
    working_directory: Path,
    run_plan: Dict[str, Any],
    approval_result: Dict[str, Any],
    install_result: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "install_failed",
        "block_reason": "Install command failed; runtime was not started.",
        "safety_mode": CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE,
        "workspace_root": str(workspace_root),
        "working_directory": str(working_directory),
        "install_result": install_result,
        "run_plan": run_plan,
        "runtime_approval": approval_result.get("approval_record"),
        "process": None,
        "logs": runtime_log_snapshot(workflow_run_id),
        "safety_flags": safe_flags(install_performed=True, node_command_executed=True),
    }


def started_response(
    workflow_run_id: str,
    process: subprocess.Popen,
    workspace_root: Path,
    working_directory: Path,
    install_result: Optional[Dict[str, Any]],
    run_plan: Dict[str, Any],
    approval_result: Dict[str, Any],
    run_command_value: Optional[str],
    run_args: list[str],
) -> Dict[str, Any]:
    poll = process.poll()
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "running" if poll is None else "exited_early",
        "block_reason": None if poll is None else "Runtime process exited before readiness confirmation.",
        "safety_mode": CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE,
        "workspace_root": str(workspace_root),
        "working_directory": str(working_directory),
        "install_result": install_result,
        "run_plan": run_plan,
        "runtime_approval": approval_result.get("approval_record"),
        "process": {
            "pid": process.pid,
            "poll": poll,
            "started": True,
            "command": run_command_value,
            "argv": run_args,
            "port": run_plan.get("port") or 5173,
        },
        "logs": runtime_log_snapshot(workflow_run_id),
        "safety_flags": safe_flags(
            runtime_started=poll is None,
            install_performed=bool(install_result),
            node_command_executed=True,
        ),
    }
