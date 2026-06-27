from __future__ import annotations

from dataclasses import replace

from app.platform.runtime.job import RuntimeJob
from app.platform.runtime.job_state import FAILED


def rollback_job(job: RuntimeJob, reason: str) -> RuntimeJob:
    return replace(job, state=FAILED, error=f"rollback: {reason}")


def rollback_available(job: RuntimeJob) -> bool:
    return bool(job.assigned_agent_id)
