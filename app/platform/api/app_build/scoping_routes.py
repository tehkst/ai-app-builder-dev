from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.platform.api.security import require_platform_admin
from app.platform.services.scoping_gateway_service import (
    analyze_scoping_request,
    approve_scoping_request,
)


router = APIRouter()


@router.post("/scoping/analyze")
def analyze_app_build_scope(
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return analyze_scoping_request(payload)


@router.post("/scoping/approve")
def approve_app_build_scope(
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return approve_scoping_request(payload)
