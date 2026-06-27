from __future__ import annotations

from dataclasses import replace

from app.platform.runtime.job import RuntimeJob
from app.platform.runtime.job_state import ASSIGNED, COMPLETED, FAILED, QUEUED, RUNNING


def queue_job(job: RuntimeJob) -> RuntimeJob:
    return replace(job, state=QUEUED)


def assign_job(job: RuntimeJob, agent_id: str) -> RuntimeJob:
    return replace(job, state=ASSIGNED, assigned_agent_id=agent_id)


def start_job(job: RuntimeJob) -> RuntimeJob:
    return replace(job, state=RUNNING)


def complete_job(job: RuntimeJob) -> RuntimeJob:
    return replace(job, state=COMPLETED)


def fail_job(job: RuntimeJob, error: str) -> RuntimeJob:
    return replace(job, state=FAILED, error=error)
