from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.platform.persistence.database import get_platform_db
from app.platform.services.mission_runtime import run_mission_runtime, format_mission_runtime_markdown

router = APIRouter(prefix="/platform/mission-runtime", tags=["platform"])


class MissionRuntimeRequest(BaseModel):
    token: Optional[str] = None
    goal: str
    requested_by: str = "founder"
    sprint_days: int = Field(default=7, ge=1, le=30)
    capacity_points: int = Field(default=20, ge=1, le=100)
    scope: str = "mission_control"


@router.post("/run")
def run(payload: MissionRuntimeRequest, db: Session = Depends(get_platform_db)) -> Dict[str, Any]:
    runtime = run_mission_runtime(
        goal=payload.goal,
        requested_by=payload.requested_by,
        sprint_days=payload.sprint_days,
        capacity_points=payload.capacity_points,
        db=db,
        scope=payload.scope,
    )
    return {
        "mission_runtime": runtime,
        "markdown": format_mission_runtime_markdown(runtime),
    }
