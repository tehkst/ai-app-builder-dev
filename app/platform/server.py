from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="AI Software Factory", version="1.0.0")


@app.get("/")
def root():
    return {"service": "ai-software-factory", "status": "running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/ready")
def ready():
    return {"status": "ready"}
