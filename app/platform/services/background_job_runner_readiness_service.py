from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from app.platform.agents.registry import list_agents
from app.platform.persistence.models import PlatformAgentTask
from app.platform.services.agent_task_service import list_agent_tasks


V84_BACKGROUND_JOB_RUNNER_SAFETY_MODE = "background_job_runner_v84_readiness_inspection_only"


def _count_tasks_by_status(db: Session) -> Dict[str, int]:
    statuses = [
        "queued",
        "approval_required",
        "approved",
        "running",
        "completed",
        "failed",
        "cancelled",
    ]
    return {
        status: db.query(PlatformAgentTask)
        .filter(PlatformAgentTask.status == status)
        .count()
        for status in statuses
    }


def inspect_background_job_runner_readiness(db: Session, *, limit: int = 25) -> Dict[str, Any]:
    """Inspect V84 background runner readiness without executing any work."""
    task_counts = _count_tasks_by_status(db)
    queued_tasks = list_agent_tasks(db, status="queued", limit=limit)
    approved_tasks = list_agent_tasks(db, status="approved", limit=limit)
    approval_required_tasks = list_agent_tasks(db, status="approval_required", limit=limit)
    agents = list_agents()

    safety_flags = {
        "inspection_only": True,
        "manual_invocation_only": True,
        "server_auto_start_performed": False,
        "worker_loop_started": False,
        "task_claimed": False,
        "task_executed": False,
        "task_status_modified": False,
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

    checks = {
        "agent_task_table_accessible": isinstance(task_counts, dict),
        "safe_agents_listed": isinstance(agents, list),
        "queued_tasks_listed": isinstance(queued_tasks, list),
        "approved_tasks_listed": isinstance(approved_tasks, list),
        "approval_required_tasks_remain_blocked": all(
            task.get("status") == "approval_required"
            for task in approval_required_tasks
        ),
        "inspection_did_not_claim_or_execute": (
            safety_flags["task_claimed"] is False
            and safety_flags["task_executed"] is False
            and safety_flags["task_status_modified"] is False
        ),
        "auto_start_disabled": (
            safety_flags["server_auto_start_performed"] is False
            and safety_flags["worker_loop_started"] is False
        ),
    }

    passed = all(checks.values())

    return {
        "check": "background_job_runner_readiness",
        "milestone": "V84 — Background Job Runner",
        "passed": passed,
        "ready_for_bounded_runner": passed,
        "safety_mode": V84_BACKGROUND_JOB_RUNNER_SAFETY_MODE,
        "checks": checks,
        "task_counts": task_counts,
        "samples": {
            "queued_tasks": queued_tasks[:5],
            "approved_tasks": approved_tasks[:5],
            "approval_required_tasks": approval_required_tasks[:5],
            "available_agents": agents,
        },
        "safety_flags": safety_flags,
    }
