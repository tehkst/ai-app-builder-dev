from __future__ import annotations

from app.platform.ui.founder_dashboard_board_chat import render_board_chat_dashboard


def main() -> None:
    html = render_board_chat_dashboard()

    assert "var token=localStorage.getItem('mission_control_token')||'';" in html
    assert "document.addEventListener('DOMContentLoaded'" in html
    assert "post('/mission-control/auth/session',{token:token})" in html
    assert "async function login()" in html

    auth_script_position = html.index("var token=localStorage.getItem('mission_control_token')||'';")
    feature_script_position = html.index("window.renderConversationIntelligence=function")
    assert auth_script_position < feature_script_position

    assert "JS_REPLACEMENT" not in html
    assert "window.newBoardChat=function" in html
    assert "window.createWorkflow=async function" in html

    print("DASHBOARD SCRIPT BOUNDARY CHECK PASSED")


if __name__ == "__main__":
    main()
