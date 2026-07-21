# Split from the legacy module to keep each Python file under 200 lines.
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.platform.persistence.models import PlatformAgentTask, PlatformApprovalRequest
from app.platform.events.agent_task_lifecycle_publisher import publish_agent_task_lifecycle
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

    generated_task_id = f"task_{uuid.uuid4().hex}"

    telegram_send_result = None

    if approval_required and not approval_id:
        approval = PlatformApprovalRequest(
            approval_id=f"approval_{uuid.uuid4().hex}",
            title=f"Approve agent task: {title.strip()}",
            description=description or f"Approval required before running agent task {generated_task_id}.",
            status="pending",
            risk_level=risk_level,
            requested_by=requested_by,
            source_type="agent_task",
            source_id=generated_task_id,
            action_type=task_type.strip(),
            action_payload_json=_json_dumps({
                "task_id": generated_task_id,
                "task_type": task_type.strip(),
                "input_payload": input_payload or {},
            }),
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            project_id=project_id,
            chat_channel="telegram",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(approval)
        db.flush()
        approval_id = approval.approval_id

    task = PlatformAgentTask(
        task_id=generated_task_id,
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

    if approval_required and approval_id:
        try:
            telegram_send_result = send_approval_to_telegram(
                db=db,
                approval_id=approval_id,
            )
        except TelegramApprovalSendError as exc:
            telegram_send_result = {
                "sent": False,
                "approval_id": approval_id,
                "error": str(exc),
            }

    task_data = serialize_agent_task(task)
    if telegram_send_result is not None:
        task_data["telegram_send_result"] = telegram_send_result

    # Organizational memory is downstream of canonical PlatformAgentTask
    # persistence. Event publication must never precede db.commit().
    publish_agent_task_lifecycle(
        task_data,
        lifecycle_status=status,
        assigned_agent=assigned_agent,
    )

    return task_data
