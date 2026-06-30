from __future__ import annotations

from app.platform.ui.mission_control import render_dashboard


def main() -> None:
    html = render_dashboard()
    assert "Mission Control" in html
    assert "Executive Office" in html
    assert "AI Workforce" in html
    assert "Knowledge Vault" in html
    assert "Company operating headquarters" in html
    assert "<!doctype html>" in html
    print("MISSION CONTROL UI CHECK PASSED")


if __name__ == "__main__":
    main()
