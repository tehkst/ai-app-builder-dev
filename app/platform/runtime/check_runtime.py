from __future__ import annotations

from app.platform.runtime.execution_engine import complete_job, queue_job
from app.platform.runtime.job import RuntimeJob
from app.platform.runtime.job_state import COMPLETED, CREATED, QUEUED


def main() -> None:
    job = RuntimeJob(
        job_id="job1",
        workflow_id="workflow1",
        task_id="task1",
        required_capability="backend_builder_task",
        priority=1,
    )
    assert job.state == CREATED
    queued = queue_job(job)
    assert queued.state == QUEUED
    done = complete_job(queued)
    assert done.state == COMPLETED
    print("RUNTIME CHECK PASSED")


if __name__ == "__main__":
    main()
