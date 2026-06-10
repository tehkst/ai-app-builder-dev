from __future__ import annotations

from fastapi import APIRouter

from app.platform.api.app_build import APP_BUILD_ROUTERS


router = APIRouter(prefix="/platform/app-build", tags=["platform-app-build"])

for app_build_router in APP_BUILD_ROUTERS:
    router.include_router(app_build_router)
