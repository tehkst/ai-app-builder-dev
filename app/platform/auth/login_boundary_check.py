from __future__ import annotations

from unittest.mock import patch

from app.platform.auth.service import build_auth_summary, login_founder
from app.platform.server import login_page, mission_control_ui
from app.platform.ui.auth_safe_dashboard import render_dashboard_fallback


def main() -> None:
    login_html = login_page()
    assert "Mission Control" in login_html or "login" in login_html.lower()

    auth = build_auth_summary()
    assert auth["status"] in {"auth-ready", "login-ready", "founder-auth-ready"}

    login = login_founder({"email": "toni.teh@gmail.com", "password": "founder"})
    assert login.get("authenticated") is True or login.get("status") in {"authenticated", "login-success"}

    fallback = render_dashboard_fallback(RuntimeError("simulated dashboard failure"))
    assert "Mission Control Safe Mode" in fallback
    assert "Login boundary is active" in fallback

    with patch("app.platform.ui.auth_safe_dashboard.render_dashboard", side_effect=RuntimeError("simulated dashboard failure"), create=True):
        safe_html = mission_control_ui()
        assert "Mission Control Safe Mode" in safe_html

    print("LOGIN BOUNDARY CHECK PASSED")


if __name__ == "__main__":
    main()
