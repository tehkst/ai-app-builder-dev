from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.platform.persistence.database import get_platform_db
from app.platform.services.board_room_orchestrator import format_orchestration_markdown, run_executive_orchestration

router = APIRouter(prefix="/platform/board-room", tags=["platform"])


class ExecutiveCoordinationRequest(BaseModel):
    token: Optional[str] = None
    message: str
    scope: str = "mission_control"


@router.post("/coordinate")
def coordinate(payload: ExecutiveCoordinationRequest, db: Session = Depends(get_platform_db)) -> Dict[str, Any]:
    orchestration = run_executive_orchestration(message=payload.message, db=db, scope=payload.scope)
    return {
        "orchestration": orchestration,
        "markdown": format_orchestration_markdown(orchestration),
    }
