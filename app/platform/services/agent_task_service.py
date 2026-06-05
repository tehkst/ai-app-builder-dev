import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformAgentTask


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


def _json_dumps(value: Optional[Dict[str, Any]]) -> str:
    return json.dumps(value or {}, sort_keys=True)


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


def create_agent_task(
    db: Session,
    *,
    title: str,
    task_type: str,
    description: Optional[str] = None,
    priority: str = "normal",
    risk_level: str = "medium",
    requested_by: str = "ai_agent",
    assigned_agent: Optional[str] = None,
    input_payload: Optional[Dict[str, Any]] = None,
    approval_required: bool = False,
    approval_id: Optional[str] = None,
    parent_task_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    project_id: Optional[str] = None,
    max_attempts: int = 3,
) -> Dict[str, Any]:
    if not title.strip():
        raise HTTPException(status_code=400, detail="Task title is required")

    if not task_type.strip():
        raise HTTPException(status_code=400, detail="Task type is required")

    if priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")

    if risk_level not in VALID_RISK_LEVELS:
        raise HTTPException(status_code=400, detail=f"Invalid risk level: {risk_level}")

    status = "approval_required" if approval_required else "queued"

    task = PlatformAgentTask(
        task_id=f"task_{uuid.uuid4().hex}",
        title=title.strip(),
        description=description,
        status=status,
        priority=priority,
        risk_level=risk_level,
        task_type=task_type.strip(),
        requested_by=requested_by,
        assigned_agent=assigned_agent,
        input_payload_json=_json_dumps(input_payload),
        result_payload_json="{}",
        approval_required=approval_required,
        approval_id=approval_id,
        parent_task_id=parent_task_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
        max_attempts=max_attempts,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    db.add(task)
    db.commit()
    db.refresh(task)
    return serialize_agent_task(task)


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
