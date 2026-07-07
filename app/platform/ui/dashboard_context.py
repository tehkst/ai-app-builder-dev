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


def build_dashboard_context() -> DashboardContext:
    mc = build_mission_control_summary()
    console = build_founder_console_summary()
    auth = build_auth_summary()

    return DashboardContext(
        founder_email=escape(os.getenv("FOUNDER_EMAIL", "founder@ai-software-factory.local")),
        ai_status=escape(f"{console['runtime']['ai_provider']} · {console['runtime']['model']}"),
        environment=escape(str(getattr(mc, "environment", "production"))),
        region=escape(str(getattr(mc, "region", "asia-southeast1"))),
        auth_status=escape(str(auth.get("status", "unknown"))),
    )
