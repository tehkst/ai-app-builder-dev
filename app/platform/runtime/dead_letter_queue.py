from __future__ import annotations

from typing import List

from app.platform.runtime.job import RuntimeJob
from app.platform.runtime.job_state import FAILED


def failed_jobs(jobs: List[RuntimeJob]) -> List[RuntimeJob]:
    return [job for job in jobs if job.state == FAILED]


def max_attempts_reached(attempt_count: int, max_attempts: int) -> bool:
    return attempt_count >= max_attempts
