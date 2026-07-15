from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformAgentTask
from app.platform.services.agent_task_service.part_1 import _json_dumps, serialize_agent_task, utc_now


DEFAULT_LEASE_SECONDS = 120


def renew_agent_task_lease(db: Session, *, task_id: str, lease_owner: str) -> bool:
    if not task_id or not lease_owner:
        return False
    renewed = db.query(PlatformAgentTask).filter(
        PlatformAgentTask.task_id == task_id,
        PlatformAgentTask.status == "running",
        PlatformAgentTask.assigned_agent == lease_owner,
    ).update(
        {PlatformAgentTask.claimed_at: utc_now(), PlatformAgentTask.updated_at: utc_now()},
        synchronize_session=False,
    )
    db.commit()
    return renewed == 1


def recover_expired_agent_tasks(db: Session, *, lease_seconds: int = DEFAULT_LEASE_SECONDS) -> int:
    cutoff = utc_now() - timedelta(seconds=max(1, lease_seconds))
    recovered = db.query(PlatformAgentTask).filter(
        PlatformAgentTask.status == "running",
        PlatformAgentTask.claimed_at < cutoff,
        PlatformAgentTask.attempts < PlatformAgentTask.max_attempts,
    ).update(
        {PlatformAgentTask.status: "queued", PlatformAgentTask.assigned_agent: None, PlatformAgentTask.updated_at: utc_now()},
        synchronize_session=False,
    )
    db.commit()
    return int(recovered)


def finalize_claimed_agent_task(
    db: Session,
    *,
    task_id: str,
    lease_owner: str,
    status: str,
    result_payload: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> dict[str, Any] | None:
    if status not in {"completed", "failed"}:
        raise ValueError("Claimed task finalization requires completed or failed status")
    now = utc_now()
    values: dict[Any, Any] = {
        PlatformAgentTask.status: status,
        PlatformAgentTask.updated_at: now,
        PlatformAgentTask.result_payload_json: _json_dumps(result_payload),
        PlatformAgentTask.error_message: error_message if status == "failed" else None,
    }
    if status == "completed":
        values[PlatformAgentTask.completed_at] = now
    else:
        values[PlatformAgentTask.failed_at] = now
    finalized = db.query(PlatformAgentTask).filter(
        PlatformAgentTask.task_id == task_id,
        PlatformAgentTask.status == "running",
        PlatformAgentTask.assigned_agent == lease_owner,
    ).update(values, synchronize_session=False)
    db.commit()
    if finalized != 1:
        return None
    task = db.query(PlatformAgentTask).filter(PlatformAgentTask.task_id == task_id).first()
    return serialize_agent_task(task)
