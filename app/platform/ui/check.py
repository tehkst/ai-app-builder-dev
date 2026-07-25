from __future__ import annotations

from app.platform.ui.mission_control import render_dashboard


def main() -> None:
    html = render_dashboard()
    assert "Mission Control" in html
    assert "Jarvis" in html
    assert 'data-section="organisation">Organisation' in html
    assert "if(name==='agents')name='organisation'" in html
    assert "Founder Experience" in html
    assert "Capability does not grant authority" in html
    assert "<!doctype html>" in html
    print("MISSION CONTROL UI CHECK PASSED")


if __name__ == "__main__":
    main()
