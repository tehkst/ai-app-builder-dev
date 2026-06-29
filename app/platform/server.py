from __future__ import annotations

from fastapi import FastAPI

from app.platform.health import build_health_status, build_readiness_status

app = FastAPI(title="AI Software Factory", version="1.0.0")


@app.get("/")
def root():
    return {"service": "ai-software-factory", "status": "running"}


@app.get("/health")
def health():
    return build_health_status()


@app.get("/ready")
def ready():
    return build_readiness_status()
