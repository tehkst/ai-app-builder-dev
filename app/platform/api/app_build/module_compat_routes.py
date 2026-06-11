from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from app.platform.api.security import require_platform_admin
from app.platform.services.self_build_module_request_service import (
    create_self_build_module_request,
    get_self_build_module_request,
    list_self_build_module_requests,
)


router = APIRouter()


@router.post("/module/create")
def create_platform_function_module(
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return create_self_build_module_request(
        module_name=payload.get("module_name"),
        module_goal=payload.get("module_goal"),
        requested_by=str(payload.get("requested_by") or "platform_admin"),
        workflow_run_id=payload.get("workflow_run_id"),
        acceptance_criteria=payload.get("acceptance_criteria") or [],
        notes=payload.get("notes"),
        initial_status="pending",
    )


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
