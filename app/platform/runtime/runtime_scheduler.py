from __future__ import annotations

from typing import List, Optional

from app.platform.runtime.job import RuntimeJob
from app.platform.runtime.job_queue import next_job
from app.platform.runtime.worker import RuntimeWorker
from app.platform.runtime.worker_pool import workers_for_capability


def select_worker_for_job(job: RuntimeJob) -> Optional[RuntimeWorker]:
    workers = workers_for_capability(job.required_capability)
    if not workers:
        return None
    return sorted(workers, key=lambda worker: (worker.active_job_count, worker.worker_id))[0]


def select_next_job(jobs: List[RuntimeJob]) -> Optional[RuntimeJob]:
    return next_job(jobs)
