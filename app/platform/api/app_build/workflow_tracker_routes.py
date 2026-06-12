from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.services.admin_workflow_tracking_service import (
    confirm_scope_and_code,
    get_workflow,
    self_heal_workflow,
    start_workflow,
)


router = APIRouter()


@router.post("/workflow-tracker/start")
def start_admin_workflow_tracker(
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return start_workflow(db, payload)


@router.post("/workflow-tracker/confirm-code")
def confirm_admin_workflow_scope_and_code(
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return confirm_scope_and_code(db, payload)


@router.post("/workflow-tracker/self-heal")
def self_heal_admin_workflow_tracker(
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return self_heal_workflow(db, payload)


@router.get("/workflow-tracker/{workflow_id}")
def get_admin_workflow_tracker(
    workflow_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return get_workflow(db, workflow_id)
