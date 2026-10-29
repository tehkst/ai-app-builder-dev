"""Check for cancelling missions (a gap from the pilot: a stuck or unwanted job could only be left
alone). A mission that isn't running is cancelled at once; a running one stops at its next AI call
without using up an attempt or pausing; a request that arrives as the run ends still cancels it; a
finished mission can't be cancelled. Scripted employees, no network."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest import mock

from app.platform.orca import MissionStore, Orca, cancel, runner
from app.platform.orca.orca_check import PLAN, Pod, finish, new_workspace, write


def check_not_running(base: Path, store: MissionStore) -> None:
    orca = Orca(chat=Pod({"Software Architect": [*finish("p1", PLAN)]}), store=store, sandbox_base=base)
    mission = orca.start_mission("Add a greeting feature", str(new_workspace(base, "idle")))
    assert orca.run(mission.mission_id).status == "awaiting_execution_approval"
    cancelled = orca.cancel_mission(mission.mission_id, decided_by="toni@example.com")
    assert cancelled.status == "cancelled" and cancelled.finished, cancelled.status
    event = cancelled.events[-1]
    assert event["event"] == "cancelled" and event["decided_by"] == "toni@example.com" and event["was"] == "awaiting_execution_approval"
    assert orca.run(mission.mission_id).status == "cancelled", "a cancelled mission never runs again"
    try:
        orca.cancel_mission(mission.mission_id)
        raise AssertionError("cancelled twice")
    except ValueError as exc:
        assert "already cancelled" in str(exc), exc


def check_running_stops_at_next_call(base: Path, store: MissionStore) -> None:
    pod = Pod({"Software Architect": [*finish("p1", PLAN)],
               "Builder": [*write("b1", "greet.py", "def greet():\n    return 'hello'\n", "done")],
               "QA Lead": [*finish("q1", {"verdict": "PASS", "evidence": "ok", "issues": []})]})
    calls = []

    def chat(messages, tools):
        calls.append(messages[0]["content"][:20])
        if messages[0]["content"].startswith("# Builder"):
            cancel.request(mission.mission_id, "toni@example.com")  # the founder clicks Cancel mid-build
        return pod(messages, tools)

    orca = Orca(chat=chat, store=store, sandbox_base=base)
    mission = orca.start_mission("Add a greeting feature", str(new_workspace(base, "busy")))
    orca.run(mission.mission_id)
    orca.decide_execution(mission.mission_id, approved=True)
    mission = orca.run(mission.mission_id)
    assert mission.status == "cancelled", (mission.status, mission.paused_reason)
    task = mission.tasks[0]
    assert task.attempts == 0 and task.status == "pending", "the interrupted attempt isn't counted"
    assert sum(c.startswith("# Builder") for c in calls) == 1, "no AI call after the request"
    assert not any(c.startswith("# QA Lead") for c in calls), "the stopped build isn't reviewed"
    events = [e["event"] for e in mission.events]
    assert "paused" not in events and events[-1] == "cancelled", events
    assert mission.events[-1]["decided_by"] == "toni@example.com"
    assert not cancel.requested(mission.mission_id), "the request is used up"
    assert store.load(mission.mission_id).status == "cancelled"


def check_request_as_run_ends(base: Path, store: MissionStore) -> None:
    """The run stops for its own reason just as the founder cancels: the runner still cancels it."""
    orca = Orca(chat=Pod({"Software Architect": [*finish("p1", PLAN)]}), store=store, sandbox_base=base)
    mission = orca.start_mission("Add a greeting feature", str(new_workspace(base, "late")))
    orca.run(mission.mission_id)

    def run_then_cancel(mission_id, *args, **kwargs):
        cancel.request(mission_id, "toni@example.com")  # arrives after the run's last check
        return store.load(mission_id)

    with mock.patch.object(orca, "run", run_then_cancel):
        assert runner.start_background_run(mission.mission_id, lambda: orca)
        for _ in range(100):
            if not runner.is_running(mission.mission_id):
                break
            time.sleep(0.05)
    assert store.load(mission.mission_id).status == "cancelled"
    assert not cancel.requested(mission.mission_id)


def check_finished_cant_be_cancelled(base: Path, store: MissionStore) -> None:
    orca = Orca(chat=Pod({}), store=store, sandbox_base=base)
    mission = orca.start_mission("Add a greeting feature", str(new_workspace(base, "done")))
    mission.status = "complete"
    store.save(mission)
    try:
        orca.cancel_mission(mission.mission_id)
        raise AssertionError("a finished mission was cancelled")
    except ValueError as exc:
        assert "already complete" in str(exc), exc
    escalated = orca.start_mission("Add a greeting feature", str(new_workspace(base, "stuck")))
    escalated.status = "escalated"
    store.save(escalated)
    assert orca.cancel_mission(escalated.mission_id).status == "cancelled", "a stuck mission can be cancelled"


def main() -> None:
    with tempfile.TemporaryDirectory() as root:
        base = Path(root, "sandboxes")
        base.mkdir()
        store = MissionStore(Path(root, "missions"))
        check_not_running(base, store)
        check_running_stops_at_next_call(base, store)
        check_request_as_run_ends(base, store)
        check_finished_cant_be_cancelled(base, store)
    print("ORCA CANCEL CHECK PASSED")


if __name__ == "__main__":
    main()
