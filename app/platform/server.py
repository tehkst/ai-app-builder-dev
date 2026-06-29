from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI

from app.platform.ai_workforce.service import build_workforce_summary
from app.platform.executive_office.service import build_executive_briefing
from app.platform.health import build_health_status, build_readiness_status
from app.platform.logging.install import install_request_logging
from app.platform.mission_control.service import build_mission_control_summary

app = FastAPI(title="AI Software Factory", version="1.0.0")
install_request_logging(app)


@app.get("/")
def root():
    return {"service": "ai-software-factory", "status": "running"}


@app.get("/health")
def health():
    return build_health_status()


@app.get("/ready")
def ready():
    return build_readiness_status()


@app.get("/mission-control")
def mission_control():
    return asdict(build_mission_control_summary())


@app.get("/mission-control/summary")
def mission_control_summary():
    return asdict(build_mission_control_summary())


@app.get("/mission-control/health")
def mission_control_health():
    summary = build_mission_control_summary()
    return {
        "service": "mission-control",
        "company": summary.company,
        "status": summary.health,
        "environment": summary.environment,
        "region": summary.region,
    }


@app.get("/mission-control/version")
def mission_control_version():
    summary = build_mission_control_summary()
    return {
        "service": "mission-control",
        "version": summary.version,
        "environment": summary.environment,
    }


@app.get("/mission-control/executive-office")
def executive_office():
    return build_executive_briefing()


@app.get("/mission-control/workforce")
def workforce():
    return build_workforce_summary()
