from __future__ import annotations

import os
import signal
import subprocess
from typing import Any, Dict

from app.platform.services.controlled_runtime_logs import mark_runtime_log_exit, runtime_log_snapshot
from app.platform.services.controlled_runtime_registry import RUNNING_PROCESSES
from app.platform.services.controlled_runtime_safety import CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE, safe_flags


def get_controlled_sandbox_runtime_status(workflow_run_id: str) -> Dict[str, Any]:
    process = RUNNING_PROCESSES.get(workflow_run_id)
    if not process:
        return _not_started(workflow_run_id)

    poll = process.poll()
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "running" if poll is None else "exited",
        "safety_mode": CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE,
        "process": {"pid": process.pid, "poll": poll, "running": poll is None},
        "logs": runtime_log_snapshot(workflow_run_id),
        "safety_flags": safe_flags(runtime_started=poll is None, node_command_executed=True),
    }


def get_controlled_sandbox_runtime_logs(workflow_run_id: str) -> Dict[str, Any]:
    return runtime_log_snapshot(workflow_run_id)


def stop_controlled_sandbox_runtime(workflow_run_id: str) -> Dict[str, Any]:
    process = RUNNING_PROCESSES.get(workflow_run_id)
    if not process:
        return _not_started(workflow_run_id)

    if process.poll() is None:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            process.wait(timeout=10)

    mark_runtime_log_exit(workflow_run_id, process.poll())
    logs = runtime_log_snapshot(workflow_run_id)
    RUNNING_PROCESSES.pop(workflow_run_id, None)
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "stopped",
        "safety_mode": CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE,
        "process": {"pid": process.pid, "poll": process.poll(), "running": False},
        "logs": logs,
        "safety_flags": safe_flags(runtime_started=False, node_command_executed=True),
    }


def _not_started(workflow_run_id: str) -> Dict[str, Any]:
    return {
        "success": True,
        "found": False,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "not_started",
        "safety_mode": CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE,
        "process": None,
        "logs": runtime_log_snapshot(workflow_run_id),
        "safety_flags": safe_flags(),
    }
