from __future__ import annotations

from app.platform.runtime.dead_letter_queue import failed_jobs, max_attempts_reached
from app.platform.runtime.execution_audit import audit_transition
from app.platform.runtime.execution_engine import assign_job, fail_job
from app.platform.runtime.execution_history import append_history, last_state
from app.platform.runtime.failure_classifier import DEPENDENCY, POLICY, TRANSIENT, classify_failure, is_retryable
from app.platform.runtime.job import RuntimeJob
from app.platform.runtime.recovery_engine import DEAD_LETTER, ESCALATE, RETRY, recovery_action
from app.platform.runtime.retry_policy import default_retry_policy
from app.platform.runtime.rollback_engine import rollback_available, rollback_job


def main() -> None:
    assert classify_failure("timeout while running") == TRANSIENT
    assert classify_failure("dependency import failed") == DEPENDENCY
    assert classify_failure("policy rejected") == POLICY
    assert is_retryable(TRANSIENT) is True
    assert is_retryable(POLICY) is False

    policy = default_retry_policy()
    assert recovery_action("timeout", 1, policy) == RETRY
    assert recovery_action("policy rejected", 1, policy) == ESCALATE
    assert recovery_action("timeout", policy.max_attempts, policy) == DEAD_LETTER

    job = RuntimeJob(
        job_id="recovery_job",
        workflow_id="workflow1",
        task_id="task1",
        required_capability="backend_builder_task",
        priority=1,
    )
    assigned = assign_job(job, "backend_builder_agent")
    assert rollback_available(assigned) is True
    rolled_back = rollback_job(assigned, "test")
    assert "rollback" in (rolled_back.error or "")

    failed = fail_job(job, "timeout")
    assert failed_jobs([failed]) == [failed]
    assert max_attempts_reached(3, 3) is True

    event = audit_transition(job.job_id, job.state, failed.state)
    history = append_history([], event)
    assert last_state(history) == failed.state

    print("RUNTIME RECOVERY CHECK PASSED")


if __name__ == "__main__":
    main()
