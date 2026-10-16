from __future__ import annotations

import os
from unittest.mock import patch

from app.platform.auth.service import build_auth_summary, login_founder
from app.platform.server import login_page, mission_control_classic, mission_control_ui
from app.platform.ui.auth_safe_dashboard import render_dashboard_fallback


def main() -> None:
    env = dict(os.environ)
    env.update(
        {
            "FOUNDER_EMAIL": "founder@ai-software-factory.local",
            "FOUNDER_PASSWORD": "local-test-password",
            "MISSION_CONTROL_SESSION_SECRET": "local-test-session-secret",
        }
    )
    with patch.dict(os.environ, env, clear=True):
        login_html = login_page()
        assert "Mission Control" in login_html or "login" in login_html.lower()

        auth = build_auth_summary()
        assert auth["status"] == "auth-ready"

        login = login_founder({"email": "founder@ai-software-factory.local", "password": "local-test-password"})
        assert login.get("authenticated") is True
        assert login.get("status") == "authenticated"

    fallback = render_dashboard_fallback(RuntimeError("simulated dashboard failure"))
    assert "Mission Control Safe Mode" in fallback
    assert "Login boundary is active" in fallback

    with patch("app.platform.ui.mission_control.render_dashboard", side_effect=RuntimeError("simulated dashboard failure")):
        safe_html = mission_control_classic()
        assert "Mission Control Safe Mode" in safe_html
        assert "Login boundary is active" in safe_html

    with patch("app.platform.ui.mc2.render_mission_control_v2", side_effect=RuntimeError("simulated redesign failure")):
        safe_html = mission_control_ui()
        assert "Mission Control Safe Mode" in safe_html and "/mission-control/classic" in safe_html
        assert "Login boundary is active" in safe_html

    print("LOGIN BOUNDARY CHECK PASSED")


if __name__ == "__main__":
    main()
