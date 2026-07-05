from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.platform.persistence.database import get_platform_db
from app.platform.services.sprint_engine import create_autonomous_sprint, format_sprint_markdown

router = APIRouter(prefix="/platform/sprint-engine", tags=["platform"])


class SprintPlanRequest(BaseModel):
    token: Optional[str] = None
    goal: str
    sprint_days: int = Field(default=7, ge=1, le=30)
    capacity_points: int = Field(default=20, ge=1, le=100)
    scope: str = "mission_control"


@router.post("/plan")
def plan(payload: SprintPlanRequest, db: Session = Depends(get_platform_db)) -> Dict[str, Any]:
    sprint_plan = create_autonomous_sprint(
        goal=payload.goal,
        sprint_days=payload.sprint_days,
        capacity_points=payload.capacity_points,
        db=db,
        scope=payload.scope,
    )
    return {
        "sprint_plan": sprint_plan,
        "markdown": format_sprint_markdown(sprint_plan),
    }
