from __future__ import annotations

import uuid
from typing import Any, Dict

from app.platform.agents import builtin  # noqa: F401 - registers built-in agents
from app.platform.persistence.database import PlatformSessionLocal
from app.platform.services.agent_task_service import create_agent_task, get_agent_task
from app.platform.services.bounded_background_job_runner_service import (
    V84_BOUNDED_BACKGROUND_JOB_RUNNER_SAFETY_MODE,
    run_bounded_background_job_once,
)


def _create_task(db, *, token: str, title: str, purpose: str, approval_required: bool = False) -> Dict[str, Any]:
    return create_agent_task(
        db,
        title=f"{title} {token}",
        task_type="worker_loop_test",
        description=f"V84 bounded runner smoke task: {title}.",
        priority="normal",
        risk_level="low" if not approval_required else "medium",
        requested_by="smoke_check",
        assigned_agent="test_agent",
        input_payload={"token": token, "purpose": purpose},
        approval_required=approval_required,
    )


def _safe_flags_preserved(flags: Dict[str, bool], *, executed_expected: bool) -> bool:
    return (
        flags.get("manual_invocation_only") is True
        and flags.get("bounded_single_task") is True
        and flags.get("explicit_task_id_required") is True
        and flags.get("allowlisted_agent_only") is True
        and flags.get("allowlisted_task_type_only") is True
        and flags.get("v84_seed_task_only") is True
        and flags.get("server_auto_start_performed") is False
        and flags.get("worker_loop_started") is False
        and flags.get("task_claimed") is executed_expected
        and flags.get("task_executed") is executed_expected
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


def run_bounded_background_job_runner_check() -> Dict[str, Any]:
    token = uuid.uuid4().hex[:10]
    db = PlatformSessionLocal()
    try:
        valid = _create_task(
            db,
            token=token,
            title="V84 valid bounded runner task",
            purpose="v84_bounded_runner_seed",
        )
        non_seed = _create_task(
            db,
            token=token,
            title="V84 non seed bounded runner task",
            purpose="not_v84_bounded_runner_seed",
        )
        approval_required = _create_task(
            db,
            token=token,
            title="V84 approval required bounded runner task",
            purpose="v84_bounded_runner_seed",
            approval_required=True,
        )

        valid_before = get_agent_task(db, valid["task_id"])
        non_seed_before = get_agent_task(db, non_seed["task_id"])
        approval_before = get_agent_task(db, approval_required["task_id"])
    finally:
        db.close()

    non_seed_result = run_bounded_background_job_once(task_id=non_seed["task_id"])
    approval_result = run_bounded_background_job_once(task_id=approval_required["task_id"])
    valid_result = run_bounded_background_job_once(task_id=valid["task_id"])
    second_valid_result = run_bounded_background_job_once(task_id=valid["task_id"])

    db = PlatformSessionLocal()
    try:
        valid_after = get_agent_task(db, valid["task_id"])
        non_seed_after = get_agent_task(db, non_seed["task_id"])
        approval_after = get_agent_task(db, approval_required["task_id"])
    finally:
        db.close()

    checks = {
        "non_seed_rejected": (
            non_seed_result.get("success") is False
            and non_seed_result.get("reason") == "task_not_allowed_for_v84_bounded_runner"
            and non_seed_after.get("status") == non_seed_before.get("status") == "queued"
            and non_seed_after.get("attempts") == non_seed_before.get("attempts")
        ),
        "approval_required_rejected": (
            approval_result.get("success") is False
            and approval_result.get("reason") == "task_not_allowed_for_v84_bounded_runner"
            and approval_after.get("status") == approval_before.get("status") == "approval_required"
            and approval_after.get("attempts") == approval_before.get("attempts")
        ),
        "valid_seed_completed": (
            valid_result.get("success") is True
            and valid_result.get("executed") is True
            and valid_result.get("status") == "completed"
            and valid_before.get("status") == "queued"
            and valid_after.get("status") == "completed"
            and valid_after.get("attempts") == valid_before.get("attempts") + 1
            and valid_after.get("claimed_at") is not None
            and valid_after.get("completed_at") is not None
        ),
        "valid_seed_not_reexecuted": (
            second_valid_result.get("success") is False
            and second_valid_result.get("reason") == "task_not_allowed_for_v84_bounded_runner"
        ),
        "safe_agent_result": (
            (valid_result.get("result") or {}).get("agent_id") == "test_agent"
            and (valid_result.get("result") or {}).get("task_type") == "worker_loop_test"
        ),
        "negative_safety_flags_preserved": (
            _safe_flags_preserved(non_seed_result.get("safety_flags") or {}, executed_expected=False)
            and _safe_flags_preserved(approval_result.get("safety_flags") or {}, executed_expected=False)
            and _safe_flags_preserved(second_valid_result.get("safety_flags") or {}, executed_expected=False)
        ),
        "valid_safety_flags_preserved": _safe_flags_preserved(
            valid_result.get("safety_flags") or {},
            executed_expected=True,
        ),
    }

    passed = all(checks.values())
    return {
        "check": "bounded_background_job_runner_check",
        "milestone": "V84 — Background Job Runner",
        "passed": passed,
        "safety_mode": V84_BOUNDED_BACKGROUND_JOB_RUNNER_SAFETY_MODE,
        "checks": checks,
        "task_ids": {
            "valid": valid["task_id"],
            "non_seed": non_seed["task_id"],
            "approval_required": approval_required["task_id"],
        },
        "results": {
            "non_seed_result": non_seed_result,
            "approval_result": approval_result,
            "valid_result": valid_result,
            "second_valid_result": second_valid_result,
        },
        "samples": {
            "valid_before": valid_before,
            "valid_after": valid_after,
            "non_seed_before": non_seed_before,
            "non_seed_after": non_seed_after,
            "approval_before": approval_before,
            "approval_after": approval_after,
        },
    }


def main() -> int:
    result = run_bounded_background_job_runner_check()
    print(result)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
