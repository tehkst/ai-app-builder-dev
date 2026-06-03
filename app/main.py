from fastapi import FastAPI

from app.api.routes import projects

from app.api.routes import auth
from app.platform.api.routes import router as platform_router

app = FastAPI(title="AI Software Factory API")

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


@app.get("/health")
async def health_check():
    return {"ok": True}
