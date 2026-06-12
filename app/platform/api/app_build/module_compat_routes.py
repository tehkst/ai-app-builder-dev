from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.services.module_requirements_service import (
    accept_module_requirements_scope,
    amend_module_requirements_scope,
    create_module_requirements_scope,
    reject_module_requirements_scope,
)
from app.platform.services.self_build_module_request_service import (
    get_self_build_module_request,
    list_self_build_module_requests,
)


router = APIRouter()


@router.post("/module/create")
def create_platform_function_module(
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return create_module_requirements_scope(db, payload)


@router.get("/module/list")
def list_platform_function_modules(
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return list_self_build_module_requests()


@router.get("/module/get")
def get_platform_function_module(
    request_id: str = Query(...),
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return get_self_build_module_request(request_id)


@router.post("/module/scope/accept")
def accept_platform_function_module_scope(
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return accept_module_requirements_scope(db, payload)


@router.post("/module/scope/reject")
def reject_platform_function_module_scope(
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return reject_module_requirements_scope(payload)


@router.post("/module/scope/amend")
def amend_platform_function_module_scope(
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return amend_module_requirements_scope(db, payload)
