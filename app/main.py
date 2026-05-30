from fastapi import FastAPI

from app.api.routes import projects

from app.api.routes import auth

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


@app.get("/health")
async def health_check():
    return {"ok": True}
