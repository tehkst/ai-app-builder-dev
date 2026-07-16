from __future__ import annotations

from typing import Any, Dict, Optional

from app.platform.agents import builtin  # noqa: F401 - registers built-in agents
from app.platform.agents.registry import get_agent
from app.platform.persistence.database import PlatformSessionLocal
from app.platform.services.agent_task_service import get_agent_task, update_agent_task_status


V84_BOUNDED_BACKGROUND_JOB_RUNNER_SAFETY_MODE = "background_job_runner_v84_bounded_manual_runner"
_ALLOWED_AGENT_ID = "test_agent"
_ALLOWED_TASK_TYPE = "worker_loop_test"
_ALLOWED_PURPOSE = "v84_bounded_runner_seed"


def _safe_flags(*, task_claimed: bool, task_executed: bool) -> Dict[str, bool]:
    return {
        "manual_invocation_only": True,
        "bounded_single_task": True,
        "explicit_task_id_required": True,
        "allowlisted_agent_only": True,
        "allowlisted_task_type_only": True,
        "v84_seed_task_only": True,
        "server_auto_start_performed": False,
        "worker_loop_started": False,
        "task_claimed": task_claimed,
        "task_executed": task_executed,
        "approval_gates_preserved": True,
        "auto_approval_performed": False,
        "approval_bypass_performed": False,
        "generated_files_written": False,
        "generated_code_execution_performed": False,
        "runtime_server_started": False,
        "repair_execution_performed": False,
        "rollout_execution_performed": False,
        "deployment_performed": False,
    }


def _is_allowed_v84_task(task: Dict[str, Any]) -> bool:
    payload = task.get("input_payload") or {}
    return (
        task.get("status") == "queued"
        and task.get("assigned_agent") == _ALLOWED_AGENT_ID
        and task.get("task_type") == _ALLOWED_TASK_TYPE
        and payload.get("purpose") == _ALLOWED_PURPOSE
        and task.get("approval_required") is False
    )


def run_bounded_background_job_once(*, task_id: str, requested_by: str = "smoke_check") -> Dict[str, Any]:
    """Run exactly one explicitly identified V84 seed task.

    This is not a daemon and does not poll the queue. It only executes a task that
    was intentionally created for the V84 bounded-runner smoke check.
    """
    db = PlatformSessionLocal()
    task_claimed = False
    task_executed = False
    try:
        task = get_agent_task(db, task_id)
        if not _is_allowed_v84_task(task):
            return {
                "success": False,
                "executed": False,
                "reason": "task_not_allowed_for_v84_bounded_runner",
                "task": task,
                "requested_by": requested_by,
                "safety_mode": V84_BOUNDED_BACKGROUND_JOB_RUNNER_SAFETY_MODE,
                "safety_flags": _safe_flags(task_claimed=False, task_executed=False),
            }

        running = update_agent_task_status(db, task_id=task_id, status="running")
        task_claimed = True
        agent = get_agent(_ALLOWED_AGENT_ID)
        if agent is None:
            failed = update_agent_task_status(
                db,
                task_id=task_id,
                status="failed",
                error_message="Allowed V84 smoke agent is not registered.",
                lease_owner=_ALLOWED_AGENT_ID,
            )
            return {
                "success": False,
                "executed": False,
                "reason": "allowed_agent_not_registered",
                "task": failed,
                "requested_by": requested_by,
                "safety_mode": V84_BOUNDED_BACKGROUND_JOB_RUNNER_SAFETY_MODE,
                "safety_flags": _safe_flags(task_claimed=task_claimed, task_executed=False),
            }

        result = agent.handler(running)
        task_executed = True
        if result.get("success") is False:
            failed = update_agent_task_status(
                db,
                task_id=task_id,
                status="failed",
                result_payload=result,
                error_message=result.get("error") or "V84 bounded runner task failed.",
                lease_owner=_ALLOWED_AGENT_ID,
            )
            return {
                "success": False,
                "executed": True,
                "status": "failed",
                "task": failed,
                "result": result,
                "requested_by": requested_by,
                "safety_mode": V84_BOUNDED_BACKGROUND_JOB_RUNNER_SAFETY_MODE,
                "safety_flags": _safe_flags(task_claimed=task_claimed, task_executed=task_executed),
            }

        completed = update_agent_task_status(
            db,
            task_id=task_id,
            status="completed",
            result_payload=result,
            lease_owner=_ALLOWED_AGENT_ID,
        )
        return {
            "success": True,
            "executed": True,
            "status": "completed",
            "task_id": task_id,
            "agent_id": _ALLOWED_AGENT_ID,
            "task": completed,
            "result": result,
            "requested_by": requested_by,
            "safety_mode": V84_BOUNDED_BACKGROUND_JOB_RUNNER_SAFETY_MODE,
            "safety_flags": _safe_flags(task_claimed=task_claimed, task_executed=task_executed),
        }
    finally:
        db.close()
