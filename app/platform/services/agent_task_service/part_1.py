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

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _json_default(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)

def _json_dumps(value: Optional[Dict[str, Any]]) -> str:
    return json.dumps(value or {}, sort_keys=True, default=_json_default)

def _json_loads(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}

def serialize_agent_task(task: PlatformAgentTask) -> Dict[str, Any]:
    return {
        "id": task.id,
        "task_id": task.task_id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "risk_level": task.risk_level,
        "task_type": task.task_type,
        "requested_by": task.requested_by,
        "assigned_agent": task.assigned_agent,
        "input_payload": _json_loads(task.input_payload_json),
        "result_payload": _json_loads(task.result_payload_json),
        "error_message": task.error_message,
        "approval_required": task.approval_required,
        "approval_id": task.approval_id,
        "parent_task_id": task.parent_task_id,
        "tenant_id": task.tenant_id,
        "workspace_id": task.workspace_id,
        "project_id": task.project_id,
        "attempts": task.attempts,
        "max_attempts": task.max_attempts,
        "scheduled_for": task.scheduled_for.isoformat() if task.scheduled_for else None,
        "claimed_at": task.claimed_at.isoformat() if task.claimed_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "failed_at": task.failed_at.isoformat() if task.failed_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }
