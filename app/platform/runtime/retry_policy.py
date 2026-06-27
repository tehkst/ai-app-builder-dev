from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int
    base_delay_seconds: int


def default_retry_policy() -> RetryPolicy:
    return RetryPolicy(max_attempts=3, base_delay_seconds=5)


def should_retry(attempt_number: int, policy: RetryPolicy) -> bool:
    return attempt_number < policy.max_attempts


def retry_delay_seconds(attempt_number: int, policy: RetryPolicy) -> int:
    return policy.base_delay_seconds * max(1, attempt_number)
