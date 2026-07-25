from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from api import router
from models import SessionLocal, initialize
from security import ensure_secret


ROOT = Path(__file__).parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_secret()
    initialize()
    yield


app = FastAPI(title="__APPLICATION_NAME__", lifespan=lifespan)
app.include_router(router)
app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")


@app.get("/", response_class=HTMLResponse)
def home():
    return (ROOT / "index.html").read_text(encoding="utf-8")


@app.get("/health")
def health():
    return {"status": "healthy", "application_id": "__APPLICATION_ID__"}


@app.get("/ready")
def ready():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}
