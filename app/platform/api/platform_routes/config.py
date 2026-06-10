from fastapi import APIRouter, Depends, Request

from app.platform.api.security import require_platform_admin
from app.platform.security.rate_limit import PLATFORM_API_RATE_LIMIT, limiter
from app.platform.services.production_config_service import (
    build_provider_checklist,
    inspect_production_config,
)


router = APIRouter()


@router.get("/config/readiness")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def get_platform_config_readiness(
    request: Request,
    platform_admin=Depends(require_platform_admin),
):
    return inspect_production_config()


@router.get("/config/checklist")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def get_platform_config_checklist(
    request: Request,
    platform_admin=Depends(require_platform_admin),
):
    return {"success": True, "provider_checklist": build_provider_checklist()}
