from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.platform.persistence.database import get_platform_db
from app.platform.services.repository_executor_gateway import (
    create_repository_executor_approval_gateway,
    format_gateway_markdown,
)

router = APIRouter(prefix="/platform/repository-executor", tags=["platform"])


class RepositoryExecutorGatewayRequest(BaseModel):
    token: Optional[str] = None
    goal: str
    requested_by: str = "founder"
    scope: str = "mission_control"


@router.post("/approval-gateway")
def approval_gateway(payload: RepositoryExecutorGatewayRequest, db: Session = Depends(get_platform_db)) -> Dict[str, Any]:
    gateway = create_repository_executor_approval_gateway(
        goal=payload.goal,
        requested_by=payload.requested_by,
        db=db,
        scope=payload.scope,
    )
    return {
        "approval_gateway": gateway,
        "markdown": format_gateway_markdown(gateway),
    }
