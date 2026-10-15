from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.services.nautilus_repair_service import (
    apply_nautilus_repair_proposal,
    get_nautilus_repair_proposals,
    propose_nautilus_repair,
)


router = APIRouter()


@router.post("/runs/{workflow_run_id}/repair-proposal/nautilus")
def post_app_build_nautilus_repair_proposal(
    workflow_run_id: str,
    db: Session = Depends(get_platform_db),
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    # The sandbox is resolved from the workflow run, never taken from the request.
    return propose_nautilus_repair(
        db=db,
        workflow_run_id=workflow_run_id,
        requested_by="platform_admin",
    )


@router.get("/runs/{workflow_run_id}/repair-proposal/nautilus/history")
def get_app_build_nautilus_repair_proposals(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return get_nautilus_repair_proposals(workflow_run_id)


@router.post("/runs/{workflow_run_id}/repair-execution/apply-nautilus-proposal")
def post_app_build_apply_nautilus_repair_proposal(
    workflow_run_id: str,
    payload: Optional[Dict[str, Any]] = Body(default=None),
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return apply_nautilus_repair_proposal(
        workflow_run_id=workflow_run_id,
        proposal_id=str((payload or {}).get("proposal_id") or "") or None,
        requested_by="platform_admin",
    )
