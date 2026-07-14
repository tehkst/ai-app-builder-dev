from __future__ import annotations

import os
from dataclasses import dataclass
from html import escape

from app.platform.auth.service import build_auth_summary
from app.platform.founder_console.service import build_founder_console_summary
from app.platform.mission_control.service import build_mission_control_summary


@dataclass(frozen=True)
class DashboardContext:
    founder_email: str
    ai_status: str
    environment: str
    region: str
    auth_status: str
    build_identity: str
    build_details: str


def build_dashboard_context() -> DashboardContext:
    mc = build_mission_control_summary()
    console = build_founder_console_summary()
    auth = build_auth_summary()
    version = str(getattr(mc, "version", "") or "").strip()
    environment = str(getattr(mc, "environment", "") or "").strip()
    commit = _first_env("GIT_COMMIT_SHA", "COMMIT_SHA", "SOURCE_COMMIT", "GITHUB_SHA")
    revision = _first_env("K_REVISION", "CLOUD_RUN_REVISION")

    return DashboardContext(
        founder_email=escape(os.getenv("FOUNDER_EMAIL", "founder@ai-software-factory.local")),
        ai_status=escape(f"{console['runtime']['ai_provider']} · {console['runtime']['model']}"),
        environment=escape(environment or "local"),
        region=escape(str(getattr(mc, "region", "asia-southeast1"))),
        auth_status=escape(str(auth.get("status", "unknown"))),
        build_identity=escape(_compact_build_identity(version, environment, commit, revision)),
        build_details=escape(_build_details(version, environment, commit, revision, _first_env("K_SERVICE"))),
    )


def _first_env(*names: str) -> str:
    return next((str(os.getenv(name) or "").strip() for name in names if str(os.getenv(name) or "").strip()), "")


def _compact_build_identity(version: str, environment: str, commit: str, revision: str) -> str:
    values = []
    if version:
        values.append(version if version.lower().startswith("v") else f"v{version}")
    if environment:
        values.append("PROD" if environment.lower() == "production" else environment.upper())
    if commit:
        values.append(commit[:8])
    if revision:
        parts = revision.split("-")
        values.append("-".join(parts[-2:]) if len(parts) > 2 else revision)
    return " · ".join(values)


def _build_details(version: str, environment: str, commit: str, revision: str, service: str) -> str:
    values = [("Version", version), ("Environment", environment), ("Git commit", commit), ("Cloud Run service", service), ("Cloud Run revision", revision)]
    return " | ".join(f"{label}: {value}" for label, value in values if value)
