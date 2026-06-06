from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.platform.agents.app_build_request_run_check import run_app_build_request
from app.platform.api.security import require_platform_admin


router = APIRouter(prefix="/platform/app-build", tags=["platform-app-build"])


class AppBuildRunRequest(BaseModel):
    app_request: str = Field(..., min_length=1)
    workflow_name: Optional[str] = None
    real_bridge: bool = False


@router.post("/run")
def run_app_build(
    request: AppBuildRunRequest,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return run_app_build_request(
        app_request=request.app_request,
        workflow_name=request.workflow_name,
        real_bridge=request.real_bridge,
    )
