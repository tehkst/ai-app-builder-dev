"""Check for Mission Control v2 (stage 1): the route serves the redesigned shell from the production
app, the structure matches the approved prototype, and the scripts parse."""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.platform.server import app
from app.platform.ui.mc2.home_script import HOME_SCRIPT
from app.platform.ui.mc2.jarvis_panel import JARVIS_SCRIPT
from app.platform.ui.mc2.page import SECTIONS


def check_route_and_structure() -> None:
    response = TestClient(app).get("/mission-control/v2")
    assert response.status_code == 200 and "text/html" in response.headers["content-type"], response.status_code
    html = response.text
    nav = re.findall(r'data-mc-nav="([a-z]+)">([^<]+)<', html)
    assert nav == [("home", "Home"), ("customers", "Customers"), ("company", "Company"), ("settings", "Settings")], nav
    assert [key for key, _ in SECTIONS] == ["home", "customers", "company", "settings"]
    assert html.count('class="mc-btn mc-open-jarvis"') == 4, "every screen needs an Ask Jarvis button"
    assert html.count("<textarea") == 1, "Jarvis must be the only place to type"
    for marker in ('id="mcNeedsYou"', 'id="mcWorkList"', 'id="mcDetail"', 'id="mcJarvis"', 'href="/mission-control/ui"'):
        assert marker in html, marker
    for removed in ("Projects", "Workflows", "Executions", "Board Room</"):
        assert removed not in re.sub(r"<script>.*?</script>", "", html, flags=re.S), f"{removed} should be gone"


def check_script_contracts() -> None:
    for endpoint in ("/mission-control/orca/missions", "/mission-control/orca/mission", "/mission-control/execution",
                     "/mission-control/publish-requests/list", "/mission-control/auth/session"):
        assert endpoint in HOME_SCRIPT, endpoint
    assert "/mission-control/operating-console/chat" in JARVIS_SCRIPT
    assert "conversation_history" in JARVIS_SCRIPT and "board_room_response" in JARVIS_SCRIPT
    assert "window.openOrcaMission" in JARVIS_SCRIPT and "window.confirm" in JARVIS_SCRIPT, "hand-off needs founder confirm"
    assert "indexOf('/mission-control/')!==0" in JARVIS_SCRIPT, "post buttons must stay inside Mission Control"
    for name in ("requestUiUxIteration", "approveUiUxChange", "mergeUiUxPullRequest"):
        assert "window." + name + "=" in JARVIS_SCRIPT and "'" + name + "'" in JARVIS_SCRIPT, f"{name} handler missing"
    for phrase in ("I APPROVE GITHUB EXECUTION", "I APPROVE PR MERGE"):
        assert phrase in JARVIS_SCRIPT, f"{phrase} gate missing"
    assert "state.selected!==key" in HOME_SCRIPT, "stale mission details must be discarded"
    assert "esc(m.text)" in JARVIS_SCRIPT and "esc(i.title)" in HOME_SCRIPT and "esc(hist)" in HOME_SCRIPT


def check_javascript_parses() -> None:
    node = shutil.which("node")
    if node is None:
        print("  (node not installed: JavaScript syntax check skipped)")
        return
    for name, source in (("home", HOME_SCRIPT), ("jarvis", JARVIS_SCRIPT)):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
            handle.write(source)
        result = subprocess.run([node, "--check", handle.name], capture_output=True, text=True)
        Path(handle.name).unlink()
        assert result.returncode == 0, f"{name} script has a syntax error:\n{result.stderr}"


def main() -> None:
    check_route_and_structure()
    check_script_contracts()
    check_javascript_parses()
    print("MISSION CONTROL V2 CHECK PASSED")


if __name__ == "__main__":
    main()
