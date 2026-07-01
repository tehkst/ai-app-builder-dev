from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.platform.health import build_health_status, build_readiness_status
from app.platform.logging.install import install_request_logging
from app.platform.ui.landing import render_login_page, render_public_landing

app = FastAPI(title="AI Software Factory", version="1.0.0")
install_request_logging(app)


@app.get("/", response_class=HTMLResponse)
def root():
    return render_public_landing()


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return render_login_page()


@app.get("/status")
def status():
    return {"service": "ai-software-factory", "status": "running"}


@app.get("/health")
def health():
    return build_health_status()


@app.get("/ready")
def ready():
    return build_readiness_status()
