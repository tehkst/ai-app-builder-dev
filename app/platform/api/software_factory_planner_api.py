from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.platform.persistence.database import get_platform_db
from app.platform.services.software_factory_planner import create_software_factory_plan, format_factory_plan_markdown

router = APIRouter(prefix="/platform/software-factory", tags=["platform"])


class SoftwareFactoryPlanRequest(BaseModel):
    token: Optional[str] = None
    goal: str
    scope: str = "mission_control"


@router.post("/plan")
def plan(payload: SoftwareFactoryPlanRequest, db: Session = Depends(get_platform_db)) -> Dict[str, Any]:
    factory_plan = create_software_factory_plan(goal=payload.goal, db=db, scope=payload.scope)
    return {
        "factory_plan": factory_plan,
        "markdown": format_factory_plan_markdown(factory_plan),
    }
