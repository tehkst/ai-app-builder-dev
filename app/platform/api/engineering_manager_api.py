from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.platform.persistence.database import get_platform_db
from app.platform.services.engineering_manager import create_engineering_spec, format_engineering_spec_markdown

router = APIRouter(prefix="/platform/engineering-manager", tags=["platform"])


class EngineeringSpecRequest(BaseModel):
    token: Optional[str] = None
    goal: str
    scope: str = "mission_control"


@router.post("/spec")
def spec(payload: EngineeringSpecRequest, db: Session = Depends(get_platform_db)) -> Dict[str, Any]:
    engineering_spec = create_engineering_spec(goal=payload.goal, db=db, scope=payload.scope)
    return {
        "engineering_spec": engineering_spec,
        "markdown": format_engineering_spec_markdown(engineering_spec),
    }
