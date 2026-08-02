from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.services.scoping_persistence_service import (
    approve_scoping_record,
    get_scoping_record,
    list_recent_scoping_records,
)
from app.platform.services.scoping_persistence_service import persist_scoping_analysis
from app.platform.services.scoping_gateway_service import (
    analyze_scoping_request,
    approve_scoping_request,
)


router = APIRouter()


@router.post("/scoping/analyze")
def analyze_app_build_scope(
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    result = analyze_scoping_request(payload)
    record = persist_scoping_analysis(db, result=result, llm_result={"status": "not_applicable"})
    return {**result, **record, "success": True}


@router.post("/scoping/approve")
def approve_app_build_scope(
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    result = approve_scoping_request(payload)
    if result.get("success") is False:
        return result
    scoping_request_id = str(payload.get("scoping_request_id") or "")
    if scoping_request_id:
        record = approve_scoping_record(db, scoping_request_id=scoping_request_id)
        if record is not None:
            return {**result, **record, "success": True}
    return result


@router.get("/scoping/recent")
def list_recent_app_build_scopes(
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return {"success": True, "requests": list_recent_scoping_records(db)}


@router.get("/scoping/{scoping_request_id}")
def get_app_build_scope(
    scoping_request_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    record = get_scoping_record(db, scoping_request_id=scoping_request_id)
    if record is None:
        return {"success": False, "status": "not_found"}
    from app.platform.services.scoping_persistence_service import serialize_scoping_record

    return {"success": True, **serialize_scoping_record(record)}
