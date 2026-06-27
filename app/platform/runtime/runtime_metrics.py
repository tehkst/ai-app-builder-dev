from __future__ import annotations

from typing import Dict, List

from app.platform.runtime.job import RuntimeJob
from app.platform.runtime.job_state import FAILED, QUEUED, RUNNING
from app.platform.runtime.worker import RuntimeWorker


def runtime_metrics(jobs: List[RuntimeJob], workers: List[RuntimeWorker]) -> Dict[str, int]:
    return {
        "job_count": len(jobs),
        "queued_job_count": len([job for job in jobs if job.state == QUEUED]),
        "running_job_count": len([job for job in jobs if job.state == RUNNING]),
        "failed_job_count": len([job for job in jobs if job.state == FAILED]),
        "worker_count": len(workers),
        "available_worker_count": len([worker for worker in workers if worker.status == "available"]),
    }
