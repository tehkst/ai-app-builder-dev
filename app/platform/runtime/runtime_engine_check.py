from __future__ import annotations

from app.platform.runtime.execution_engine import queue_job
from app.platform.runtime.job import RuntimeJob
from app.platform.runtime.job_queue import next_job, queue_depth
from app.platform.runtime.job_state import QUEUED
from app.platform.runtime.resource_manager import can_start_job, worker_has_capacity
from app.platform.runtime.retry_policy import default_retry_policy, retry_delay_seconds, should_retry
from app.platform.runtime.runtime_monitor import runtime_snapshot
from app.platform.runtime.runtime_scheduler import select_next_job, select_worker_for_job
from app.platform.runtime.worker_pool import build_worker_pool, workers_for_capability


def main() -> None:
    job = RuntimeJob(
        job_id="runtime_engine_job",
        workflow_id="constitution_foundation_workflow",
        task_id="implement_constitution_registry",
        required_capability="backend_builder_task",
        priority=1,
    )
    queued = queue_job(job)
    assert queued.state == QUEUED, queued
    assert queue_depth([queued]) == 1
    assert next_job([queued]) == queued
    assert select_next_job([queued]) == queued

    workers = build_worker_pool()
    assert workers, workers
    backend_workers = workers_for_capability("backend_builder_task")
    assert backend_workers, backend_workers
    worker = select_worker_for_job(queued)
    assert worker is not None, queued
    assert worker.agent_id == "backend_builder_agent", worker

    policy = default_retry_policy()
    assert should_retry(1, policy) is True
    assert retry_delay_seconds(2, policy) == 10

    assert can_start_job(0) is True
    assert worker_has_capacity(0) is True

    snapshot = runtime_snapshot([queued], list(workers.values()))
    assert snapshot["metrics"]["job_count"] == 1, snapshot
    assert snapshot["metrics"]["worker_count"] >= 1, snapshot

    print("RUNTIME ENGINE CHECK PASSED")


if __name__ == "__main__":
    main()
