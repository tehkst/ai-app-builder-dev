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

def claim_next_agent_task(
    db: Session,
    *,
    assigned_agent: str,
    task_type: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if not assigned_agent.strip():
        raise HTTPException(status_code=400, detail="Assigned agent is required")

    query = db.query(PlatformAgentTask).filter(
        PlatformAgentTask.status.in_(["queued", "approved"])
    )

    if task_type:
        query = query.filter(PlatformAgentTask.task_type == task_type)

    priority_rank = {
        "urgent": 0,
        "high": 1,
        "normal": 2,
        "low": 3,
    }

    candidates = query.order_by(PlatformAgentTask.created_at.asc()).limit(50).all()

    if not candidates:
        return None

    task = sorted(
        candidates,
        key=lambda item: (
            priority_rank.get(item.priority, 99),
            item.created_at,
        ),
    )[0]

    now = utc_now()
    task.status = "running"
    task.assigned_agent = assigned_agent.strip()
    task.claimed_at = now
    task.started_at = task.started_at or now
    task.attempts = task.attempts + 1
    task.updated_at = now

    db.commit()
    db.refresh(task)
    return serialize_agent_task(task)

def sync_agent_task_approval(
    db: Session,
    *,
    task_id: str,
) -> Dict[str, Any]:
    task = (
        db.query(PlatformAgentTask)
        .filter(PlatformAgentTask.task_id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Agent task not found")

    if not task.approval_required or not task.approval_id:
        raise HTTPException(status_code=400, detail="Task has no linked approval")

    approval = (
        db.query(PlatformApprovalRequest)
        .filter(PlatformApprovalRequest.approval_id == task.approval_id)
        .first()
    )
    if not approval:
        raise HTTPException(status_code=404, detail="Linked approval not found")

    now = utc_now()

    if approval.status == "approved":
        task.status = "approved"
    elif approval.status == "rejected":
        task.status = "cancelled"
    elif approval.status == "changes_requested":
        task.status = "approval_required"
    else:
        task.status = "approval_required"

    task.updated_at = now
    db.commit()
    db.refresh(task)

    return {
        "task": serialize_agent_task(task),
        "approval": {
            "approval_id": approval.approval_id,
            "status": approval.status,
            "title": approval.title,
        },
    }
