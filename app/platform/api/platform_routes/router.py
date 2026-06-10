from fastapi import APIRouter

from app.platform.api.platform_routes.config import router as config_router
from app.platform.api.platform_routes.dashboard import router as dashboard_router
from app.platform.api.platform_routes.lists import router as lists_router
from app.platform.api.platform_routes.repair import router as repair_router


router = APIRouter(prefix="/platform", tags=["platform"])

for child_router in (dashboard_router, config_router, lists_router, repair_router):
    router.include_router(child_router)
