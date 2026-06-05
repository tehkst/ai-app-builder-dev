from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.services.agent_task_service import (
    create_agent_task,
    get_agent_task,
    list_agent_tasks,
    update_agent_task_status,
    claim_next_agent_task,
    sync_agent_task_approval,
)


router = APIRouter(prefix="/platform/agent-tasks", tags=["platform-agent-tasks"])


class CreateAgentTaskRequest(BaseModel):
    title: str = Field(..., min_length=1)
    task_type: str = Field(..., min_length=1)
    description: Optional[str] = None
    priority: str = "normal"
    risk_level: str = "medium"
    requested_by: str = "ai_agent"
    assigned_agent: Optional[str] = None
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    approval_required: bool = False
    approval_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    tenant_id: Optional[str] = None
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    max_attempts: int = 3





class ClaimNextAgentTaskRequest(BaseModel):
    assigned_agent: str = Field(..., min_length=1)
    task_type: Optional[str] = None


class UpdateAgentTaskStatusRequest(BaseModel):
    status: str
    result_payload: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


@router.post("")
def create_task(
    request: CreateAgentTaskRequest,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
):
    return create_agent_task(
        db=db,
        title=request.title,
        task_type=request.task_type,
        description=request.description,
        priority=request.priority,
        risk_level=request.risk_level,
        requested_by=request.requested_by,
        assigned_agent=request.assigned_agent,
        input_payload=request.input_payload,
        approval_required=request.approval_required,
        approval_id=request.approval_id,
        parent_task_id=request.parent_task_id,
        tenant_id=request.tenant_id,
        workspace_id=request.workspace_id,
        project_id=request.project_id,
        max_attempts=request.max_attempts,
    )


@router.get("")
def list_tasks(
    status: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    task_type: Optional[str] = None,
    limit: int = 50,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
):
    return {
        "items": list_agent_tasks(
            db=db,
            status=status,
            assigned_agent=assigned_agent,
            task_type=task_type,
            limit=limit,
        )
    }





@router.post("/claim-next")
def claim_next_task(
    request: ClaimNextAgentTaskRequest,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
):
    task = claim_next_agent_task(
        db=db,
        assigned_agent=request.assigned_agent,
        task_type=request.task_type,
    )
    return {"task": task}


@router.get("/{task_id}")
def get_task(
    task_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
):
    return get_agent_task(db=db, task_id=task_id)





@router.post("/{task_id}/sync-approval")
def sync_task_approval(
    task_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
):
    return sync_agent_task_approval(db=db, task_id=task_id)


@router.post("/{task_id}/status")
def update_task_status(
    task_id: str,
    request: UpdateAgentTaskStatusRequest,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
):
    return update_agent_task_status(
        db=db,
        task_id=task_id,
        status=request.status,
        result_payload=request.result_payload,
        error_message=request.error_message,
    )
