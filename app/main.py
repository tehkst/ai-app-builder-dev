from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import projects

from app.api.routes import auth
from app.platform.api.approval_routes import router as platform_approval_router
from app.platform.api.routes import router as platform_router
from app.platform.api.telegram_routes import router as platform_telegram_router
from app.platform.api.agent_task_routes import router as platform_agent_task_router
from app.platform.api.app_build_routes import router as platform_app_build_router
from app.platform.api.context_api import router as platform_context_router
from app.platform.api.board_room_agents_api import router as platform_board_room_agents_router
from app.platform.api.board_room_orchestrator_api import router as platform_board_room_orchestrator_router
from app.platform.api.software_factory_planner_api import router as platform_software_factory_planner_router
from app.platform.api.engineering_manager_api import router as platform_engineering_manager_router
from app.platform.api.code_executor_api import router as platform_code_executor_router
from app.platform.api.platform_auth_routes import router as platform_auth_router
from app.platform.persistence.database import create_platform_tables
from app.platform.security.rate_limit import limiter
from app.platform.security.rate_limit_audit import audited_rate_limit_exceeded_handler
from app.platform.services.production_config_service import build_healthcheck_summary

app = FastAPI(title="AI Software Factory API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, audited_rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.on_event("startup")
def startup_platform_database():
    create_platform_tables()


app.include_router(
    projects.router,
    prefix="/api/projects",
    tags=["Projects"],
)

app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["Auth"],
)

app.include_router(platform_router)
app.include_router(platform_approval_router)
app.include_router(platform_telegram_router)
app.include_router(platform_agent_task_router)
app.include_router(platform_app_build_router)
app.include_router(platform_context_router)
app.include_router(platform_board_room_agents_router)
app.include_router(platform_board_room_orchestrator_router)
app.include_router(platform_software_factory_planner_router)
app.include_router(platform_engineering_manager_router)
app.include_router(platform_code_executor_router)
app.include_router(platform_auth_router)


@app.get("/health")
async def health_check():
    return build_healthcheck_summary()


@app.get("/health/readiness")
async def readiness_check():
    return build_healthcheck_summary()
