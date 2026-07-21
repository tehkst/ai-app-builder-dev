from __future__ import annotations

from app.platform.ui.founder_dashboard_board_chat import render_board_chat_dashboard
from app.platform.ui.jarvis_experience import enhance_dashboard_with_jarvis


def render_dashboard() -> str:
    return enhance_dashboard_with_jarvis(render_board_chat_dashboard())
