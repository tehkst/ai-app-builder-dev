from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.platform.persistence.database import get_platform_db
from app.platform.services.mission_runtime_workbench import (
    create_mission_runtime_workbench,
    format_workbench_markdown,
)

router = APIRouter(prefix="/platform/mission-runtime/workbench", tags=["platform"])


class MissionRuntimeWorkbenchRequest(BaseModel):
    token: Optional[str] = None
    goal: str
    requested_by: str = "founder"
    sprint_days: int = Field(default=7, ge=1, le=30)
    capacity_points: int = Field(default=20, ge=1, le=100)
    scope: str = "mission_control"


@router.post("/run")
def run(payload: MissionRuntimeWorkbenchRequest, db: Session = Depends(get_platform_db)) -> Dict[str, Any]:
    workbench = create_mission_runtime_workbench(
        goal=payload.goal,
        requested_by=payload.requested_by,
        sprint_days=payload.sprint_days,
        capacity_points=payload.capacity_points,
        db=db,
        scope=payload.scope,
    )
    return {
        "workbench": workbench,
        "markdown": format_workbench_markdown(workbench),
    }
