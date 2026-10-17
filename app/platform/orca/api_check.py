"""Deterministic check for the Orca Mission Control API and view (no network): drives the real
production app (`app.platform.server:app`) with a founder session token, while a scripted pod
plays the employees."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from app.platform.auth.service import _sign_claims
from app.platform.orca import MissionStore, Orca, api_service, runner
from app.platform.orca.orca_check import FAIL, PASS, PLAN, Pod, finish, new_workspace, write
from app.platform.server import app
from app.platform.ui.founder_dashboard_stable import render_stable_founder_dashboard
from app.platform.ui.orca_missions_script import render_orca_missions_script


def founder_token() -> str:
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).replace(microsecond=0).isoformat()
    return _sign_claims({"sub": "founder@example.com", "role": "founder", "exp": expires})


class Api:
    def __init__(self, client: TestClient, token: str) -> None:
        self.client, self.token = client, token

    def __call__(self, path: str, **body) -> dict:
        response = self.client.post(f"/mission-control/orca/{path}", json={"token": self.token, **body})
        assert response.status_code == 200, (path, response.status_code, response.text)
        return response.json()

    def settle(self, mission_id: str) -> dict:
        runner.wait_for(mission_id, timeout=60)
        return self("mission", mission_id=mission_id)["mission"]


def happy_pod() -> Pod:
    return Pod({"Software Architect": finish("p", PLAN),
                "Builder": [*write("b1", "greet.py", "def greet():\n    return 'hello'\n", "<b>greet</b> added"),
                            *write("b2", "README.md", "# Greet\n", "docs")],
                "QA Lead": [*finish("q1", PASS), *finish("q2", PASS)]})


def check_api(base: Path, store_dir: Path) -> None:
    client = TestClient(app)
    api = Api(client, founder_token())
    anonymous = client.post("/mission-control/orca/missions", json={}).json()
    assert anonymous["status"] == "unauthorized", anonymous
    forged = client.post("/mission-control/orca/missions", json={"token": "x.y"}).json()
    assert forged["status"] == "unauthorized", forged

    new_workspace(base, "demo-app")
    (base / "bad name").mkdir()
    assert api("workspaces")["workspaces"] == ["demo-app"]
    workforce = api("workforce")
    team = {e["id"]: e for e in workforce["team"]}
    assert workforce["planned"] and all(p["name"] and p["why"] for p in workforce["planned"]), "planned hires"
    assert set(team) == {"architect", "builder", "qa_lead", "frontend_developer", "ux_designer", "code_auditor",
                         "security_reviewer"}, team
    assert team["code_auditor"]["role"] == "auditor" and team["security_reviewer"]["role"] == "reviewer"
    assert [team[i]["role"] for i in ("architect", "builder", "frontend_developer", "qa_lead", "ux_designer")] == \
        ["planner", "builder", "builder", "reviewer", "reviewer"], team
    assert all(e["summary"] for e in team.values()), "every employee needs a founder-facing summary"
    for body, message in (({"goal": "", "workspace": "demo-app"}, "goal"),
                          ({"goal": "g", "workspace": "../etc"}, "workspace"),
                          ({"goal": "g", "workspace": "missing"}, "workspace")):
        result = api("start", **body)
        assert result["status"] == "error" and message in result["error"].lower(), result

    pod = happy_pod()
    factory = lambda: Orca(chat=pod, store=MissionStore(store_dir), sandbox_base=base)  # noqa: E731
    with mock.patch.object(api_service, "_orca_factory", factory):
        started = api("start", goal="Add greet and docs", workspace="demo-app")
        assert started["status"] == "ok", started
        mission_id = started["mission"]["mission_id"]
        mission = api.settle(mission_id)
        assert mission["status"] == "awaiting_execution_approval" and len(mission["tasks"]) == 2, mission["status"]
        assert any(e["event"] == "started_from_mission_control" and e["by"] == "founder@example.com"
                   for e in mission["events"])
        assert api("run", mission_id=mission_id)["status"] == "error", "run must wait for the decision"
        assert api("decide-execution", mission_id=mission_id, approved="yes")["status"] == "error"

        api("decide-execution", mission_id=mission_id, approved=True)
        mission = api.settle(mission_id)
        assert mission["status"] == "complete", (mission["status"], mission.get("escalation"))
        assert mission["tasks"][0]["handoffs"][0]["summary"] == "<b>greet</b> added"  # raw; the view escapes
        listed = api("missions")["missions"][0]
        assert (listed["status"], listed["tasks_passed"], listed["running"]) == ("complete", 2, False), listed
        assert api("run", mission_id=mission_id)["status"] == "error"
        assert api("mission", mission_id="ORCA-NOPE00000000")["status"] == "error"

        # Board Room hand-off: the proposal id is recorded as a label; malformed ids are ignored
        linked = api("start", goal="from jarvis", workspace="demo-app", source={"board_room_mission_id": "MISSION-ABCDEF123456"})
        runner.wait_for(linked["mission"]["mission_id"], timeout=60)
        detail = api("mission", mission_id=linked["mission"]["mission_id"])["mission"]
        assert any(e["event"] == "started_from_board_room" and e["board_room_mission_id"] == "MISSION-ABCDEF123456"
                   for e in detail["events"]), detail["events"]
        assert api("missions")["missions"][0]["origin"] == "board_room"
        forged = api("start", goal="x", workspace="demo-app", source={"board_room_mission_id": "<script>"})
        runner.wait_for(forged["mission"]["mission_id"], timeout=60)
        assert forged["mission"]["origin"] == "mission_control", forged

    one = {"summary": "s", "tasks": [PLAN["tasks"][0]]}
    pod = Pod({"Software Architect": finish("p", one),
               "Builder": [t for i in range(4) for t in write(f"b{i}", "greet.py", "def greet():\n    return 'hello'\n", "x")],
               "QA Lead": [t for i in range(3) for t in finish(f"q{i}", FAIL)] + finish("ok", PASS)})
    factory = lambda: Orca(chat=pod, store=MissionStore(store_dir), sandbox_base=base)  # noqa: E731
    with mock.patch.object(api_service, "_orca_factory", factory):
        mission_id = api("start", goal="greet", workspace="demo-app", execution_approved=True)["mission"]["mission_id"]
        assert api.settle(mission_id)["status"] == "escalated"
        api("retry", mission_id=mission_id)
        assert api.settle(mission_id)["status"] == "complete"

    def crashing_factory():
        orca = Orca(chat=happy_pod(), store=MissionStore(store_dir), sandbox_base=base)
        orca.run = mock.Mock(side_effect=RuntimeError("disk full"))
        return orca

    with mock.patch.object(api_service, "_orca_factory", crashing_factory):
        mission_id = api("start", goal="crash", workspace="demo-app")["mission"]["mission_id"]
        mission = api.settle(mission_id)
        assert mission["status"] == "paused" and "disk full" in mission["paused_reason"], mission["status"]


def check_one_mission_per_workspace(base: Path, store_dir: Path) -> None:
    """Review fix: two missions must never run on the same workspace at once."""
    import threading

    api = Api(TestClient(app), founder_token())
    new_workspace(base, "busy-app")
    new_workspace(base, "other-app")
    release = threading.Event()
    pod = happy_pod()

    def held(messages, tools):
        release.wait(30)  # keep mission A busy while B tries to start
        return pod(messages, tools)

    factory = lambda: Orca(chat=held, store=MissionStore(store_dir), sandbox_base=base)  # noqa: E731
    with mock.patch.object(api_service, "_orca_factory", factory):
        first = api("start", goal="A", workspace="busy-app")["mission"]["mission_id"]
        assert runner.is_running(first)
        second = api("start", goal="B", workspace="busy-app")
        assert second["status"] == "error" and first in second["error"], second
        other = api("start", goal="C", workspace="other-app")
        assert other["status"] == "ok", other
        release.set()
        for mission_id in (first, other["mission"]["mission_id"]):
            runner.wait_for(mission_id, timeout=60)
        assert api("start", goal="D", workspace="busy-app")["status"] == "ok", "workspace freed after A stopped"
        runner.wait_for(api("missions")["missions"][0]["mission_id"], timeout=60)


def check_board_room_buttons() -> None:
    from app.platform.operating_console.action_service import (
        build_decision_ready_mission_actions, build_pending_mission_actions,
    )

    import app.platform.services.materialization_sandbox_writer_service as sandbox_base

    def orca_buttons(request: str) -> list:
        found = []
        for actions in (build_pending_mission_actions(request), build_decision_ready_mission_actions(request)):
            found.append([b for b in actions["action_buttons"] if b.get("target") == "openOrcaMission"])
        return found

    with tempfile.TemporaryDirectory() as root:
        for name in ("shopfront", "blog"):
            Path(root, name).mkdir()
        with mock.patch.object(sandbox_base, "APPROVED_SANDBOX_ROOT_BASE", Path(root)):
            request = "In the shopfront app, add a pricing page that compares the three plans"
            for buttons in orca_buttons(request):
                assert len(buttons) == 1 and buttons[0]["action_type"] == "function", buttons
                payload = buttons[0]["payload"]
                assert payload["workspace"] == "shopfront" and payload["goal"] == request, payload
                assert payload["board_room_mission_id"].startswith("MISSION-")
                assert "action_context" not in payload, "the Orca button must not carry the signed context"
            # review fix: platform proposals and unnamed/ambiguous apps get no Orca hand-off
            for request in ("Improve the Mission Control navigation so founders find Orca",
                            "Add a pricing page that compares the three plans",
                            "Make the shopfront and blog apps share a header",
                            "Add a shopfronts page to the docs"):
                assert orca_buttons(request) == [[], []], request


def check_view() -> None:
    script = render_orca_missions_script()
    assert "/mission-control/orca/" in script and "mission_control_token" in script
    assert "esc(h.summary)" in script and "esc(m.goal)" in script and "esc(e.summary)" in script, \
        "AI-written and manifest text must be escaped"
    assert "How it works" in script and "Your AI team" in script and "orca-example" in script
    assert "window.openOrcaMission" in script and "esc(payload.title" in script and "esc(ws)" in script, \
        "Board Room entry point missing"
    page = render_stable_founder_dashboard()
    assert "render_orca" not in page and "Orca Missions" in page, "script not included in the dashboard"
    node = shutil.which("node")
    if node is None:
        print("  (node not installed: JavaScript syntax check skipped)")
        return
    body = script.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
        handle.write(body)
    result = subprocess.run([node, "--check", handle.name], capture_output=True, text=True)
    Path(handle.name).unlink()
    assert result.returncode == 0, "Orca view JavaScript has a syntax error:\n" + result.stderr


def main() -> None:
    with tempfile.TemporaryDirectory() as root:
        base = Path(root, "workspaces")
        base.mkdir()
        with mock.patch.object(api_service, "APPROVED_SANDBOX_ROOT_BASE", base):
            check_api(base, Path(root, "missions"))
            check_one_mission_per_workspace(base, Path(root, "missions"))
    check_board_room_buttons()
    check_view()
    print("ORCA API CHECK PASSED")


if __name__ == "__main__":
    main()
