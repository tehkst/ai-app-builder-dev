from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.services.controlled_sandbox_runtime_service import (
    get_controlled_sandbox_runtime_logs,
    get_controlled_sandbox_runtime_status,
    start_controlled_sandbox_runtime_for_workflow,
)
from app.platform.services.repair_executor_service import get_repair_execution_history


REPAIR_RERUN_COORDINATOR_SAFETY_MODE = "repair_rerun_coordinator_v76_after_successful_repair_only"
_REPAIR_RERUN_HISTORY: Dict[str, List[Dict[str, Any]]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_flags(*, rerun_started: bool = False, blocked: bool = True) -> Dict[str, bool]:
    return {
        "repair_rerun_coordinator_checked": True,
        "successful_repair_execution_required": True,
        "successful_repair_execution_found": not blocked,
        "rerun_blocked": blocked,
        "rerun_started": rerun_started,
        "used_existing_controlled_runtime_path": True,
        "auto_approval_performed": False,
        "repair_plan_generated": False,
        "repair_applied": False,
        "restore_executed": False,
        "module_rollout_performed": False,
        "install_packages_performed": False,
        "runtime_server_started": rerun_started,
        "generated_code_execution_performed": rerun_started,
        "node_command_executed": rerun_started,
        "python_command_executed": False,
        "preview_server_started": False,
    }


def _latest_successful_repair(workflow_run_id: str) -> Optional[Dict[str, Any]]:
    history_result = get_repair_execution_history(workflow_run_id)
    history = history_result.get("history") or []
    for record in reversed(history):
        if record.get("applied") is True and record.get("execution_status") == "applied":
            return record
    return None


def _blocked_result(
    *,
    workflow_run_id: str,
    reason: str,
    before_runtime_status: Optional[Dict[str, Any]] = None,
    before_runtime_logs: Optional[Dict[str, Any]] = None,
    repair_execution_history: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": REPAIR_RERUN_COORDINATOR_SAFETY_MODE,
        "rerun_status": "blocked",
        "rerun_started": False,
        "blocked": True,
        "block_reason": reason,
        "repair_execution_history": repair_execution_history,
        "before_runtime_status": before_runtime_status,
        "before_runtime_logs": before_runtime_logs,
        "after_runtime_start": None,
        "after_runtime_status": None,
        "after_runtime_logs": None,
        "comparison": None,
        "history": _REPAIR_RERUN_HISTORY.get(workflow_run_id, []),
        "safety_flags": _safe_flags(rerun_started=False, blocked=True),
    }


def rerun_after_successful_repair(
    *,
    db: Session,
    workflow_run_id: str,
    requested_by: str = "platform_admin",
    perform_install: bool = False,
) -> Dict[str, Any]:
    repair_execution_history = get_repair_execution_history(workflow_run_id)
    latest_repair = _latest_successful_repair(workflow_run_id)
    before_status = get_controlled_sandbox_runtime_status(workflow_run_id)
    before_logs = get_controlled_sandbox_runtime_logs(workflow_run_id)

    if latest_repair is None:
        return _blocked_result(
            workflow_run_id=workflow_run_id,
            reason="Re-run is blocked until a successful repair execution exists.",
            before_runtime_status=before_status,
            before_runtime_logs=before_logs,
            repair_execution_history=repair_execution_history,
        )

    if perform_install:
        return _blocked_result(
            workflow_run_id=workflow_run_id,
            reason="V76 re-run does not perform package installation; use the existing approved runtime plan only.",
            before_runtime_status=before_status,
            before_runtime_logs=before_logs,
            repair_execution_history=repair_execution_history,
        )

    after_start = start_controlled_sandbox_runtime_for_workflow(
        db,
        workflow_run_id=workflow_run_id,
        perform_install=False,
    )
    after_status = get_controlled_sandbox_runtime_status(workflow_run_id)
    after_logs = get_controlled_sandbox_runtime_logs(workflow_run_id)

    started = after_start.get("runtime_status") in {"running", "already_running", "exited_early"}
    comparison = {
        "before_runtime_status": before_status.get("runtime_status"),
        "after_runtime_status": after_status.get("runtime_status"),
        "after_start_status": after_start.get("runtime_status"),
        "before_stdout_line_count": ((before_logs.get("logs") or {}).get("stdout_line_count") or 0),
        "before_stderr_line_count": ((before_logs.get("logs") or {}).get("stderr_line_count") or 0),
        "after_stdout_line_count": ((after_logs.get("logs") or {}).get("stdout_line_count") or 0),
        "after_stderr_line_count": ((after_logs.get("logs") or {}).get("stderr_line_count") or 0),
        "latest_repair_created_at": latest_repair.get("created_at"),
        "latest_repair_operation_count": latest_repair.get("operation_count"),
    }

    record = {
        "workflow_run_id": workflow_run_id,
        "rerun_status": "started" if started else "blocked_or_failed_to_start",
        "rerun_started": started,
        "requested_by": requested_by,
        "created_at": _now_iso(),
        "latest_repair": latest_repair,
        "comparison": comparison,
    }
    _REPAIR_RERUN_HISTORY.setdefault(workflow_run_id, []).append(record)

    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": REPAIR_RERUN_COORDINATOR_SAFETY_MODE,
        "rerun_status": record["rerun_status"],
        "rerun_started": started,
        "blocked": not started,
        "block_reason": None if started else after_start.get("block_reason") or "Runtime did not start after repair.",
        "repair_execution_history": repair_execution_history,
        "before_runtime_status": before_status,
        "before_runtime_logs": before_logs,
        "after_runtime_start": after_start,
        "after_runtime_status": after_status,
        "after_runtime_logs": after_logs,
        "comparison": comparison,
        "history": _REPAIR_RERUN_HISTORY.get(workflow_run_id, []),
        "safety_flags": _safe_flags(rerun_started=started, blocked=not started),
    }


def get_repair_rerun_history(workflow_run_id: str) -> Dict[str, Any]:
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": REPAIR_RERUN_COORDINATOR_SAFETY_MODE,
        "history": _REPAIR_RERUN_HISTORY.get(workflow_run_id, []),
        "safety_flags": _safe_flags(rerun_started=False, blocked=True),
    }


def reset_repair_rerun_history_for_check() -> None:
    _REPAIR_RERUN_HISTORY.clear()
