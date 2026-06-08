from __future__ import annotations

import uuid
from typing import Any, Dict

from app.platform.agents import builtin  # noqa: F401 - registers built-in agents
from app.platform.persistence.database import PlatformSessionLocal
from app.platform.services.agent_task_service import create_agent_task, get_agent_task
from app.platform.services.background_job_runner_readiness_service import (
    V84_BACKGROUND_JOB_RUNNER_SAFETY_MODE,
    inspect_background_job_runner_readiness,
)


def _make_task_title(prefix: str, token: str) -> str:
    return f"{prefix} {token}"


def _create_seed_tasks(db, token: str) -> Dict[str, str]:
    queued = create_agent_task(
        db,
        title=_make_task_title("V84 queued readiness task", token),
        task_type="worker_loop_test",
        description="Seed queued task for V84 background runner readiness inspection.",
        priority="normal",
        risk_level="low",
        requested_by="smoke_check",
        assigned_agent="test_agent",
        input_payload={"token": token, "purpose": "queued_readiness_seed"},
        approval_required=False,
    )
    approval_required = create_agent_task(
        db,
        title=_make_task_title("V84 approval required readiness task", token),
        task_type="worker_loop_test",
        description="Seed approval-required task for V84 gate preservation inspection.",
        priority="normal",
        risk_level="medium",
        requested_by="smoke_check",
        assigned_agent="test_agent",
        input_payload={"token": token, "purpose": "approval_required_readiness_seed"},
        approval_required=True,
    )
    return {
        "queued_task_id": queued["task_id"],
        "approval_required_task_id": approval_required["task_id"],
    }


def _safe_flags_preserved(flags: Dict[str, bool]) -> bool:
    return (
        flags.get("inspection_only") is True
        and flags.get("manual_invocation_only") is True
        and flags.get("server_auto_start_performed") is False
        and flags.get("worker_loop_started") is False
        and flags.get("task_claimed") is False
        and flags.get("task_executed") is False
        and flags.get("task_status_modified") is False
        and flags.get("approval_gates_preserved") is True
        and flags.get("auto_approval_performed") is False
        and flags.get("approval_bypass_performed") is False
        and flags.get("generated_files_written") is False
        and flags.get("generated_code_execution_performed") is False
        and flags.get("runtime_server_started") is False
        and flags.get("repair_execution_performed") is False
        and flags.get("rollout_execution_performed") is False
        and flags.get("deployment_performed") is False
    )


def run_background_job_runner_readiness_check() -> Dict[str, Any]:
    token = uuid.uuid4().hex[:10]
    db = PlatformSessionLocal()
    try:
        task_ids = _create_seed_tasks(db, token)
        queued_before = get_agent_task(db, task_ids["queued_task_id"])
        approval_before = get_agent_task(db, task_ids["approval_required_task_id"])

        readiness = inspect_background_job_runner_readiness(db, limit=100)

        queued_after = get_agent_task(db, task_ids["queued_task_id"])
        approval_after = get_agent_task(db, task_ids["approval_required_task_id"])

        checks = {
            "readiness_passed": readiness.get("passed") is True,
            "ready_for_bounded_runner": readiness.get("ready_for_bounded_runner") is True,
            "seeded_queued_task_visible": any(
                task.get("task_id") == task_ids["queued_task_id"]
                for task in (readiness.get("samples") or {}).get("queued_tasks") or []
            ),
            "seeded_approval_required_task_visible": any(
                task.get("task_id") == task_ids["approval_required_task_id"]
                for task in (readiness.get("samples") or {}).get("approval_required_tasks") or []
            ),
            "queued_task_not_claimed_or_executed": (
                queued_before.get("status") == "queued"
                and queued_after.get("status") == "queued"
                and queued_after.get("attempts") == queued_before.get("attempts")
                and queued_after.get("claimed_at") == queued_before.get("claimed_at")
            ),
            "approval_required_task_remains_blocked": (
                approval_before.get("status") == "approval_required"
                and approval_after.get("status") == "approval_required"
                and approval_after.get("attempts") == approval_before.get("attempts")
                and approval_after.get("claimed_at") == approval_before.get("claimed_at")
            ),
            "safe_agents_available": any(
                agent.get("agent_id") == "test_agent"
                for agent in (readiness.get("samples") or {}).get("available_agents") or []
            ),
            "safety_flags_preserved": _safe_flags_preserved(readiness.get("safety_flags") or {}),
        }

        passed = all(checks.values())
        return {
            "check": "background_job_runner_readiness_check",
            "milestone": "V84 — Background Job Runner",
            "passed": passed,
            "safety_mode": V84_BACKGROUND_JOB_RUNNER_SAFETY_MODE,
            "checks": checks,
            "task_ids": task_ids,
            "readiness": readiness,
            "samples": {
                "queued_before": queued_before,
                "queued_after": queued_after,
                "approval_before": approval_before,
                "approval_after": approval_after,
            },
        }
    finally:
        db.close()


def main() -> int:
    result = run_background_job_runner_readiness_check()
    print(result)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
