from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import projects

from app.api.routes import auth
from app.platform.api.approval_routes import router as platform_approval_router
from app.platform.api.routes import router as platform_router
from app.platform.persistence.database import create_platform_tables
from app.platform.security.rate_limit import limiter
from app.platform.security.rate_limit_audit import audited_rate_limit_exceeded_handler

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


@app.get("/health")
async def health_check():
    return {"ok": True}
