from __future__ import annotations

from typing import Dict


DEFAULT_LIMITS: Dict[str, int] = {
    "max_parallel_jobs": 4,
    "max_jobs_per_worker": 1,
}


def can_start_job(active_job_count: int, max_parallel_jobs: int = DEFAULT_LIMITS["max_parallel_jobs"]) -> bool:
    return active_job_count < max_parallel_jobs


def worker_has_capacity(active_job_count: int, max_jobs_per_worker: int = DEFAULT_LIMITS["max_jobs_per_worker"]) -> bool:
    return active_job_count < max_jobs_per_worker
