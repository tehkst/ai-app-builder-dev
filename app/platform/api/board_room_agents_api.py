from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.platform.persistence.database import get_platform_db
from app.platform.services.board_room_agents import format_deliberation_markdown, run_board_room_deliberation

router = APIRouter(prefix="/platform/board-room", tags=["platform"])


class BoardRoomDeliberationRequest(BaseModel):
    token: Optional[str] = None
    message: str
    scope: str = "mission_control"


@router.post("/deliberate")
def deliberate(payload: BoardRoomDeliberationRequest, db: Session = Depends(get_platform_db)) -> Dict[str, Any]:
    deliberation = run_board_room_deliberation(message=payload.message, db=db, scope=payload.scope)
    return {
        "deliberation": deliberation,
        "markdown": format_deliberation_markdown(deliberation),
    }
