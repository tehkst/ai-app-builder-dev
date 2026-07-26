from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.services.customer_app_scope_service import draft_customer_app_scope
from app.platform.services.scoping_persistence_service import (
    approve_scoping_record,
    get_scoping_record,
    list_scoping_version_chain,
    persist_scoping_analysis,
    serialize_scoping_record,
)
from app.platform.services.scoping_version_rollback_service import (
    rollback_generated_files_to_scoping_version,
)

router = APIRouter()

REQUEST_KIND = "customer_app"


class DraftProductScopeRequest(BaseModel):
    app_request: str = Field(..., min_length=1)
    requested_by: str = "platform_admin"


class AmendProductScopeRequest(BaseModel):
    app_request: str = Field(..., min_length=1)
    requested_by: str = "platform_admin"


class ApproveProductScopeRequest(BaseModel):
    approved_by: str = "platform_admin"


class RollbackProductScopeRequest(BaseModel):
    restored_by: str = "platform_admin"


@router.post("/product-scope/draft")
def draft_product_scope(
    request: DraftProductScopeRequest,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    """Draft a scope of work (SOW) for a customer app request, for the user to approve."""

    result = draft_customer_app_scope(request.app_request)
    if not result.get("success"):
        return result
    record = persist_scoping_analysis(
        db,
        result=result,
        llm_result={"status": "not_applicable"},
        requested_by=request.requested_by,
        request_kind=REQUEST_KIND,
    )
    return {**result, **record, "success": True}


@router.post("/product-scope/{scoping_request_id}/amend")
def amend_product_scope(
    scoping_request_id: str,
    request: AmendProductScopeRequest,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    """Draft a new version of a SOW as a change request against a prior version."""

    previous = get_scoping_record(db, scoping_request_id)
    if previous is None:
        return {"success": False, "status": "not_found"}

    result = draft_customer_app_scope(request.app_request)
    if not result.get("success"):
        return result
    record = persist_scoping_analysis(
        db,
        result=result,
        llm_result={"status": "not_applicable"},
        requested_by=request.requested_by,
        request_kind=REQUEST_KIND,
        previous_scoping_request_id=scoping_request_id,
    )
    return {**result, **record, "success": True}


@router.post("/product-scope/{scoping_request_id}/approve")
def approve_product_scope(
    scoping_request_id: str,
    request: Optional[ApproveProductScopeRequest] = None,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    request = request or ApproveProductScopeRequest()
    record = approve_scoping_record(db, scoping_request_id=scoping_request_id, approved_by=request.approved_by)
    if record is None:
        return {"success": False, "status": "not_found"}
    return {"success": True, **record}


@router.get("/product-scope/{scoping_request_id}")
def get_product_scope(
    scoping_request_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    record = get_scoping_record(db, scoping_request_id)
    if record is None:
        return {"success": False, "status": "not_found"}
    return {"success": True, **serialize_scoping_record(record)}


@router.get("/product-scope/{scoping_request_id}/versions")
def get_product_scope_versions(
    scoping_request_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    chain = list_scoping_version_chain(db, scoping_request_id)
    return {"success": bool(chain), "versions": chain}


@router.post("/product-scope/{scoping_request_id}/rollback")
def rollback_product_scope(
    scoping_request_id: str,
    request: Optional[RollbackProductScopeRequest] = None,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    """Restore generated files to the state they were in for this SOW version."""

    request = request or RollbackProductScopeRequest()
    return rollback_generated_files_to_scoping_version(
        db,
        scoping_request_id=scoping_request_id,
        restored_by=request.restored_by,
    )
