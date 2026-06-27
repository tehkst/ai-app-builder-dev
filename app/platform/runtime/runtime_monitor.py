from __future__ import annotations

from typing import Dict, List

from app.platform.runtime.job import RuntimeJob
from app.platform.runtime.runtime_metrics import runtime_metrics
from app.platform.runtime.worker import RuntimeWorker


def runtime_snapshot(jobs: List[RuntimeJob], workers: List[RuntimeWorker]) -> Dict[str, object]:
    return {
        "metrics": runtime_metrics(jobs, workers),
        "job_ids": [job.job_id for job in jobs],
        "worker_ids": [worker.worker_id for worker in workers],
    }
