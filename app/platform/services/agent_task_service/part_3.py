# Split from the legacy module to keep each Python file under 200 lines.
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.platform.persistence.models import PlatformAgentTask, PlatformApprovalRequest
from app.platform.services.telegram_approval_service import (
    TelegramApprovalSendError,
    send_approval_to_telegram,
)
from app.platform.services.agent_task_service.part_6 import finalize_claimed_agent_task
VALID_TASK_STATUSES = {
    "queued",
    "approval_required",
    "approved",
    "running",
    "completed",
    "failed",
    "cancelled",
}
VALID_PRIORITIES = {"low", "normal", "high", "urgent"}
VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}

def get_agent_task(db: Session, task_id: str) -> Dict[str, Any]:
    task = (
        db.query(PlatformAgentTask)
        .filter(PlatformAgentTask.task_id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Agent task not found")
    return serialize_agent_task(task)

def list_agent_tasks(
    db: Session,
    *,
    status: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    task_type: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    query = db.query(PlatformAgentTask)

    if status:
        query = query.filter(PlatformAgentTask.status == status)

    if assigned_agent:
        query = query.filter(PlatformAgentTask.assigned_agent == assigned_agent)

    if task_type:
        query = query.filter(PlatformAgentTask.task_type == task_type)

    tasks = (
        query.order_by(PlatformAgentTask.created_at.desc())
        .limit(max(1, min(limit, 200)))
        .all()
    )
    return [serialize_agent_task(task) for task in tasks]

def update_agent_task_status(
    db: Session,
    *,
    task_id: str,
    status: str,
    result_payload: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    lease_owner: Optional[str] = None,
) -> Dict[str, Any]:
    if status not in VALID_TASK_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid task status: {status}")

    task = (
        db.query(PlatformAgentTask)
        .filter(PlatformAgentTask.task_id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Agent task not found")

    if status in {"completed", "failed"} and task.status == "running" and task.assigned_agent:
        finalized = finalize_claimed_agent_task(
            db,
            task_id=task_id,
            lease_owner=str(lease_owner or ""),
            status=status,
            result_payload=result_payload,
            error_message=error_message,
        )
        if not finalized:
            raise HTTPException(status_code=409, detail="Task lease ownership changed; stale completion was rejected")
        return finalized

    now = utc_now()
    task.status = status
    task.updated_at = now

    if status == "running":
        task.started_at = task.started_at or now
        task.claimed_at = task.claimed_at or now
        task.attempts = task.attempts + 1

    if status == "completed":
        task.completed_at = now
        task.error_message = None
        if result_payload is not None:
            task.result_payload_json = _json_dumps(result_payload)

    if status == "failed":
        task.failed_at = now
        task.error_message = error_message

    db.commit()
    db.refresh(task)
    return serialize_agent_task(task)
