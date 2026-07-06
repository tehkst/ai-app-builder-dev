from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.platform.persistence.database import get_platform_db
from app.platform.services.github_credential_manager import DEFAULT_REPOSITORY
from app.platform.services.repository_execution_engine import (
    create_repository_execution_package,
    format_repository_execution_markdown,
)

router = APIRouter(prefix="/platform/repository-execution", tags=["platform"])


class RepositoryExecutionRequest(BaseModel):
    token: Optional[str] = None
    goal: str
    repository: str = DEFAULT_REPOSITORY
    requested_by: str = "founder"
    founder_approved: bool = False
    sprint_days: int = Field(default=7, ge=1, le=30)
    capacity_points: int = Field(default=20, ge=1, le=100)
    scope: str = "mission_control"


@router.post("/package")
def package(payload: RepositoryExecutionRequest, db: Session = Depends(get_platform_db)) -> Dict[str, Any]:
    execution_package = create_repository_execution_package(
        goal=payload.goal,
        repository=payload.repository,
        requested_by=payload.requested_by,
        founder_approved=payload.founder_approved,
        sprint_days=payload.sprint_days,
        capacity_points=payload.capacity_points,
        db=db,
        scope=payload.scope,
    )
    return {
        "repository_execution_package": execution_package,
        "markdown": format_repository_execution_markdown(execution_package),
    }
