from __future__ import annotations

from app.platform.ui.dashboard_context import DashboardContext
from app.platform.ui.login_module import render_login_screen, render_login_script


def render_dashboard_template(html: str, context: DashboardContext) -> str:
    build_badge = (
        '<small class="build-id" title="__BUILD_DETAILS__" '
        'style="display:block;margin-top:4px;color:#94a3b8;font-size:10px;line-height:1.3">'
        "__BUILD_IDENTITY__</small>"
    ) if context.build_identity else ""
    return (
        html.replace("<span>Mission Control</span>", "<span>Mission Control</span>" + build_badge, 1)
        .replace("__LOGIN_SCREEN__", render_login_screen())
        .replace("__LOGIN_SCRIPT__", render_login_script())
        .replace("__FOUNDER_EMAIL__", context.founder_email)
        .replace("__ENV__", context.environment)
        .replace("__REGION__", context.region)
        .replace("__AI_STATUS__", context.ai_status)
        .replace("__AUTH_STATUS__", context.auth_status)
        .replace("__BUILD_IDENTITY__", context.build_identity)
        .replace("__BUILD_DETAILS__", context.build_details)
    )
