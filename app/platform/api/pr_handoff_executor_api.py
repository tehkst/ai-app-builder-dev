from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.platform.persistence.database import get_platform_db
from app.platform.services.pr_handoff_executor import create_pr_handoff, format_pr_handoff_markdown

router = APIRouter(prefix="/platform/pr-handoff", tags=["platform"])


class PrHandoffRequest(BaseModel):
    token: Optional[str] = None
    goal: str
    requested_by: str = "founder"
    scope: str = "mission_control"


@router.post("/prepare")
def prepare(payload: PrHandoffRequest, db: Session = Depends(get_platform_db)) -> Dict[str, Any]:
    handoff = create_pr_handoff(
        goal=payload.goal,
        requested_by=payload.requested_by,
        db=db,
        scope=payload.scope,
    )
    return {
        "pr_handoff": handoff,
        "markdown": format_pr_handoff_markdown(handoff),
    }
