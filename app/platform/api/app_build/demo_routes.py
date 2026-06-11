from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.services.gym_booking_demo_service import (
    create_gym_booking_demo_run,
)


router = APIRouter()


@router.post("/demo/gym-booking")
def create_gym_booking_demo(
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return create_gym_booking_demo_run(
        db,
        created_by=str(payload.get("created_by") or "gym_app_user_001"),
    )
