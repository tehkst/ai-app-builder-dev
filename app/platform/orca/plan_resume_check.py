"""Check that planning continues after a pause instead of starting over (seen in the pilot: every
DeepSeek outage made the architect re-read the whole codebase). When the provider fails mid-plan the
architect's conversation is saved with the mission; resuming, even after a restart, replays it
without a new briefing. Too big a conversation, or a cancel, drops it. Scripted employees only."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List
from unittest import mock

from app.platform.nautilus.loop_check import call, turn
from app.platform.orca import MissionStore, Orca, engine
from app.platform.orca.orca_check import PLAN, Pod, finish, new_workspace


class Recording(Pod):
    """A Pod that also notes how long each architect conversation was when it was sent."""

    def __init__(self, scripts) -> None:
        super().__init__(scripts)
        self.sent: List[int] = []

    def __call__(self, messages, tools):
        if messages[0]["content"].startswith("# Software Architect"):
            self.sent.append(len(messages))
        return super().__call__(messages, tools)


def explore_then_fail() -> list:
    return [turn("", [call("l1", "list_files")]), turn("", [call("r1", "read_file", path="app.txt")]),
            RuntimeError("provider timeout")]


def check_resume_continues(base: Path, store: MissionStore) -> None:
    pod = Recording({"Software Architect": [*explore_then_fail(), *finish("p1", PLAN)]})
    orca = Orca(chat=pod, store=store, sandbox_base=base)
    mission = orca.run(orca.start_mission("Add a greeting", str(new_workspace(base, "resume"))).mission_id)
    assert mission.status == "paused" and mission.resume_status == "planning", mission.status
    saved = mission.plan_progress
    assert saved and saved[-1]["role"] == "tool" and "existing project" in saved[-1]["content"], saved

    restarted = Orca(chat=pod, store=MissionStore(store.directory), sandbox_base=base)  # survives a restart
    mission = restarted.run(mission.mission_id)
    assert mission.status == "awaiting_execution_approval" and len(mission.tasks) == 2, mission.status
    assert len(pod.briefings["Software Architect"]) == 1, "resuming must not brief the architect again"
    assert pod.sent[3] == len(saved), pod.sent  # the first call after resuming carries the whole earlier conversation
    assert mission.plan_progress is None, "cleared once planning ends"
    assert any(e["event"] == "planning_resumed" and e["messages"] == len(saved) for e in mission.events)


def check_too_big_restarts(base: Path, store: MissionStore) -> None:
    pod = Recording({"Software Architect": [*explore_then_fail(), *finish("p1", PLAN)]})
    orca = Orca(chat=pod, store=store, sandbox_base=base)
    with mock.patch.object(engine, "MAX_SAVED_CONVERSATION_BYTES", 10):
        mission = orca.run(orca.start_mission("Add a greeting", str(new_workspace(base, "big"))).mission_id)
    assert mission.status == "paused" and mission.plan_progress is None, mission.plan_progress
    mission = orca.run(mission.mission_id)
    assert mission.status == "awaiting_execution_approval", mission.status
    assert len(pod.briefings["Software Architect"]) == 2, "without a saved conversation planning starts over"


def check_cancel_drops_it(base: Path, store: MissionStore) -> None:
    pod = Recording({"Software Architect": explore_then_fail()})
    orca = Orca(chat=pod, store=store, sandbox_base=base)
    mission = orca.run(orca.start_mission("Add a greeting", str(new_workspace(base, "cancel"))).mission_id)
    assert mission.plan_progress
    mission = orca.cancel_mission(mission.mission_id)
    assert mission.status == "cancelled" and mission.plan_progress is None, mission.status
    assert store.load(mission.mission_id).plan_progress is None


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        store = MissionStore(base / "missions")
        check_resume_continues(base, store)
        check_too_big_restarts(base, store)
        check_cancel_drops_it(base, store)
    print("ORCA PLAN RESUME CHECK PASSED")


if __name__ == "__main__":
    main()
