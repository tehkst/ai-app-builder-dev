from __future__ import annotations

from typing import List, Optional

from app.platform.runtime.job import RuntimeJob


def sort_jobs(jobs: List[RuntimeJob]) -> List[RuntimeJob]:
    return sorted(jobs, key=lambda job: (job.priority, job.job_id))


def next_job(jobs: List[RuntimeJob]) -> Optional[RuntimeJob]:
    queue = sort_jobs(jobs)
    return queue[0] if queue else None


def queue_depth(jobs: List[RuntimeJob]) -> int:
    return len(jobs)
