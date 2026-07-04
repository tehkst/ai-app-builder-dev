from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.platform.persistence.database import get_platform_db
from app.platform.services.executive_context_service import capture_context as save_context
from app.platform.services.executive_context_service import format_context_block, list_context_items

router = APIRouter(prefix="/platform/context", tags=["platform"])


class ContextItemRequest(BaseModel):
    scope: str = "mission_control"
    kind: str = "conversation_learning"
    title: str
    body: str
    source: str = "board_room"


@router.get("")
def get_context(scope: str = "mission_control", db: Session = Depends(get_platform_db)):
    return {
        "scope": scope,
        "items": list_context_items(db=db, scope=scope),
        "context_block": format_context_block(db=db, scope=scope),
    }


@router.post("/items")
def add_context_item(payload: ContextItemRequest, db: Session = Depends(get_platform_db)):
    return save_context(
        db=db,
        scope=payload.scope,
        kind=payload.kind,
        title=payload.title,
        body=payload.body,
        source=payload.source,
    )
