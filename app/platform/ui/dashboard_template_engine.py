from __future__ import annotations

from app.platform.ui.dashboard_context import DashboardContext
from app.platform.ui.login_module import render_login_screen, render_login_script


def render_dashboard_template(html: str, context: DashboardContext) -> str:
    return (
        html.replace("__LOGIN_SCREEN__", render_login_screen())
        .replace("__LOGIN_SCRIPT__", render_login_script())
        .replace("__FOUNDER_EMAIL__", context.founder_email)
        .replace("__ENV__", context.environment)
        .replace("__REGION__", context.region)
        .replace("__AI_STATUS__", context.ai_status)
        .replace("__AUTH_STATUS__", context.auth_status)
    )
