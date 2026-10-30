"""Check job alerts and the stalled-job watchdog (orca/alerts): one alert per state change after a
background run, nothing when alerts are off or the founder cancelled, the watchdog alerting once per
quiet spell (running or orphaned) without saving the mission, a failing channel not stopping the
others, and notification text never reaching the AppleScript itself. Scripted employees; no real
notifications or email."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple
from unittest import mock

from app.platform.orca import MissionStore, Orca, alerts, runner
from app.platform.orca.orca_check import PLAN, Pod, finish, new_workspace

SENT: List[Tuple[str, str]] = []


def capture(title: str, text: str) -> None:
    SENT.append((title, text))


def broken(title: str, text: str) -> None:
    raise OSError("smtp down")


def check_after_run(base: Path, store: MissionStore) -> None:
    SENT.clear()
    pod = Pod({"Software Architect": [RuntimeError("provider timeout"), *finish("p1", PLAN)]})
    orca = Orca(chat=pod, store=store, sandbox_base=base)
    mission = orca.start_mission("Add a greeting\n\nmore detail", str(new_workspace(base, "alerts")))
    mission.client = {"client_name": "Kopi Shop"}
    store.save(mission)

    with mock.patch.dict(os.environ, {"ORCA_ALERTS": ""}):
        assert runner.start_background_run(mission.mission_id, lambda: orca)
        runner.wait_for(mission.mission_id, 30)
    assert store.load(mission.mission_id).status == "paused" and not SENT, "alerts off: nothing sent"

    with mock.patch.dict(os.environ, {"ORCA_ALERTS": "1"}), mock.patch.object(alerts, "channels", lambda: {"mac": capture}):
        assert alerts.after_run(store, mission.mission_id)["sent"] == ["mac"]
        assert SENT[-1][0] == "Kopi Shop: Add a greeting" and "paused: AI provider error" in SENT[-1][1], SENT
        assert alerts.after_run(store, mission.mission_id) is None and len(SENT) == 1, "one alert per state"
        event = store.load(mission.mission_id).events[-1]
        assert event["event"] == "alerted" and event["status"] == "paused" and event["sent"] == ["mac"], event

        assert runner.start_background_run(mission.mission_id, lambda: orca)  # resumes, plans, waits for approval
        runner.wait_for(mission.mission_id, 30)
        assert store.load(mission.mission_id).status == "awaiting_execution_approval"
        assert len(SENT) == 2 and "waiting for your approval" in SENT[-1][1], SENT

        cancelled = orca.cancel_mission(mission.mission_id)
        assert alerts.after_run(store, cancelled.mission_id) is None and len(SENT) == 2, "cancelling isn't news"


def check_failing_channel_and_script() -> None:
    with mock.patch.object(alerts, "channels", lambda: {"email": broken, "mac": capture}):
        result = alerts.notify("t", "x")
    assert result["sent"] == ["mac"] and "smtp down" in result["failed"]["email"], result

    hostile = 'done" & (do shell script "touch /tmp/pwned") & "'
    with mock.patch.object(alerts.sys, "platform", "darwin"), mock.patch.object(alerts.subprocess, "run") as run:
        alerts.mac_notification("Client", hostile)
    argv = run.call_args.args[0]
    assert argv[-1] == hostile and all(hostile not in part for part in argv[:-1]), argv

    with mock.patch("app.platform.auth.service._founder_email", lambda: "founder@ai-software-factory.local"), \
            mock.patch("app.platform.runtime.smtp_provider_router.active_smtp_config",
                       lambda: {"username": "u", "password": "p", "sender": "u", "host": "h", "port": 587}):
        assert alerts.email_settings() is None, "no real founder address: no email"
    with mock.patch("app.platform.auth.service._founder_email", lambda: "toni@example.com"), \
            mock.patch("app.platform.runtime.smtp_provider_router.active_smtp_config",
                       lambda: {"username": "u", "password": "p", "sender": "u", "host": "h", "port": 587}), \
            mock.patch.object(alerts.smtplib, "SMTP") as smtp:
        assert "email" in alerts.channels()
        alerts.send_email("[AI Software Factory] job", "The job is done.")
    server = smtp.return_value.__enter__.return_value
    mail = server.send_message.call_args.args[0]
    assert mail["To"] == "toni@example.com" and server.starttls.called and server.login.call_args.args == ("u", "p")


def check_watchdog(base: Path, store: MissionStore) -> None:
    orca = Orca(chat=Pod({}), store=store, sandbox_base=base)
    stuck = orca.start_mission("Stuck job", str(new_workspace(base, "stuck")))
    stuck.status = "building"
    store.save(stuck)
    waiting = orca.start_mission("Waiting job", str(new_workspace(base, "waiting")))
    waiting.status = "awaiting_execution_approval"
    store.save(waiting)
    soon = datetime.now(timezone.utc) + timedelta(minutes=10)
    later = datetime.now(timezone.utc) + timedelta(minutes=alerts.STALL_MINUTES + 5)
    SENT.clear()
    with mock.patch.object(alerts, "channels", lambda: {"mac": capture}):
        assert alerts.check_stalled(store, lambda _id: False, now=soon) == [], "not quiet long enough"
        assert alerts.check_stalled(store, lambda _id: False, now=later) == [stuck.mission_id], "waiting jobs aren't stalled"
        assert "nothing is running it" in SENT[-1][1] and "Press Run" in SENT[-1][1], SENT
        assert alerts.check_stalled(store, lambda _id: True, now=later) == [], "one alert per quiet spell"
        assert store.load(stuck.mission_id).events == stuck.events, "the watchdog never saves the mission"

        alerts._QUIET_ALERTED.clear()
        alerts.check_stalled(store, lambda _id: True, now=later)
        assert "no progress for" in SENT[-1][1] and "cancel and retry" in SENT[-1][1], SENT

    with mock.patch.dict(os.environ, {"ORCA_ALERTS": ""}):
        assert not alerts.start_watchdog(lambda: store, runner.is_running), "the watchdog only runs in the service"


def check_messages() -> None:
    from app.platform.orca.models import Mission

    for status in alerts.MESSAGES:
        mission = Mission("ORCA-MSG000000001", "Fix login", "/w", status=status, paused_reason="Docker isn't running",
                          escalation={"reason": "QA failed three times"})
        assert alerts.message(mission), status
    assert alerts.message(Mission("ORCA-MSG000000002", "g", "/w", status="building")) is None
    assert alerts.message(Mission("ORCA-MSG000000003", "g", "/w", status="cancelled")) is None


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        store = MissionStore(base / "missions")
        check_messages()
        check_failing_channel_and_script()
        check_after_run(base, store)
        check_watchdog(base, store)
    print("ORCA ALERTS CHECK PASSED")


if __name__ == "__main__":
    main()
