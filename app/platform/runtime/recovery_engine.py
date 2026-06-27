from __future__ import annotations

from app.platform.runtime.failure_classifier import classify_failure, is_retryable
from app.platform.runtime.retry_policy import RetryPolicy, should_retry


RETRY = "retry"
ROLLBACK = "rollback"
ESCALATE = "escalate"
DEAD_LETTER = "dead_letter"


def recovery_action(error: str, attempt_count: int, policy: RetryPolicy) -> str:
    failure_type = classify_failure(error)
    if is_retryable(failure_type) and should_retry(attempt_count, policy):
        return RETRY
    if attempt_count >= policy.max_attempts:
        return DEAD_LETTER
    if failure_type in {"policy", "agent", "permanent"}:
        return ESCALATE
    return ROLLBACK
