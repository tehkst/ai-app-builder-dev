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

def claim_next_agent_task_for_parent(
    db: Session,
    assigned_agent: str,
    parent_task_id: str,
    task_type: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    query = db.query(PlatformAgentTask).filter(
        PlatformAgentTask.status.in_(["queued", "approved"]),
        PlatformAgentTask.assigned_agent == assigned_agent,
        PlatformAgentTask.parent_task_id == parent_task_id,
    )

    if task_type:
        query = query.filter(PlatformAgentTask.task_type == task_type)

    task = (
        query.order_by(
            PlatformAgentTask.priority.desc(),
            PlatformAgentTask.created_at.asc(),
        )
        .first()
    )

    if not task:
        return None

    now = utc_now()
    task.status = "running"
    task.claimed_at = now
    task.started_at = now
    task.updated_at = now
    task.attempts += 1

    db.add(task)
    db.commit()
    db.refresh(task)

    return serialize_agent_task(task)
