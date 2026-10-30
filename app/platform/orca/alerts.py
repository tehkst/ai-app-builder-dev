"""Tell the founder when a mission needs them or is done, without opening Mission Control: a Mac
notification (no setup) and, when an email provider is set up in Settings, an email to the founder.

Two triggers:
- `after_run`: a background run ended in a state worth knowing (paused, escalated, waiting for
  answers or approval, finished, failed). One alert per state change: an alert is recorded as the
  mission's last event, so re-running a mission that is still waiting doesn't alert again.
- the watchdog: a mission that should be working has shown no activity for STALL_MINUTES, either
  because its run is stuck or because nothing is running it. One alert per quiet spell, noted in
  the mission's activity feed.

Only the always-on service sets ORCA_ALERTS=1 (app/platform/ops), so checks and dev servers never
notify. Alerts are best effort: a failure to notify is recorded and never breaks the mission.
"""
from __future__ import annotations

import os
import smtplib
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any, Callable, Dict, List, Optional

from app.platform.orca.models import Mission

STALL_MINUTES = 30
WATCH_EVERY_SECONDS = 300
# Statuses where the mission should be making progress on its own.
WORKING_STATUSES = {"planning", "building", "integration"}

MESSAGES = {
    "paused": "paused: {reason}. Fix it, then resume the job.",
    "escalated": "is stuck and needs your decision: {escalation}",
    "awaiting_decision": "has questions for you before planning.",
    "awaiting_execution_approval": "is planned and waiting for your approval to run the code.",
    "complete": "is done. Review the changes, then deliver them.",
    "complete_unverified": "is done, but not everything could be checked. Read the handover before delivering.",
    "failed": "failed: {reason}",
}


def enabled() -> bool:
    return os.getenv("ORCA_ALERTS") == "1"


def label(mission: Mission) -> str:
    """'Client: job title', or the goal's first line for the platform's own missions."""
    title = (mission.goal.strip().splitlines() or [mission.mission_id])[0][:80]
    client = (mission.client or {}).get("client_name")
    return f"{client}: {title}" if client else title


def message(mission: Mission) -> Optional[str]:
    template = MESSAGES.get(mission.status)
    if template is None:
        return None
    failed = next((e for e in reversed(mission.events) if e.get("event") == "planning_failed"), {})
    reason = mission.paused_reason or "; ".join(failed.get("problems") or []) or "see Mission Control"
    return template.format(reason=reason[:300], escalation=((mission.escalation or {}).get("reason") or "")[:300])


# ---- channels ------------------------------------------------------------------------------

def mac_notification(title: str, text: str) -> None:
    """Notification Centre via osascript. Text goes in as arguments, never into the script."""
    if sys.platform != "darwin":
        raise RuntimeError("Mac notifications only work on macOS")
    script = ["-e", "on run argv", "-e", "display notification (item 2 of argv) with title (item 1 of argv)",
              "-e", "end run"]
    subprocess.run(["osascript", *script, title[:120], text[:400]], check=True, capture_output=True, timeout=15)


def email_settings() -> Optional[Dict[str, Any]]:
    """The email provider from Settings, and the founder's address; None when either is missing."""
    from app.platform.auth.service import DEFAULT_FOUNDER_EMAIL, _founder_email
    from app.platform.runtime.smtp_provider_router import active_smtp_config

    config, to = active_smtp_config(), _founder_email()
    if not (config["username"] and config["password"] and config["sender"]) or not to or to == DEFAULT_FOUNDER_EMAIL:
        return None
    return {**config, "to": to}


def send_email(subject: str, text: str) -> None:
    config = email_settings()
    if config is None:
        raise RuntimeError("no email provider set up")
    mail = EmailMessage()
    mail["Subject"], mail["From"], mail["To"] = subject[:150], config["sender"], config["to"]
    mail.set_content(text + "\n\nOpen Mission Control: http://127.0.0.1:8000/mission-control/v2\n")
    with smtplib.SMTP(config["host"], config["port"], timeout=20) as server:
        server.starttls()
        server.login(config["username"], config["password"])
        server.send_message(mail)


Channel = Callable[[str, str], None]


def channels() -> Dict[str, Channel]:
    found: Dict[str, Channel] = {"mac": mac_notification}
    try:
        if email_settings() is not None:
            found["email"] = lambda title, text: send_email(f"[AI Software Factory] {title}", text)
    except Exception:  # settings unreadable: the Mac notification still goes out
        pass
    return found


def notify(title: str, text: str) -> Dict[str, Any]:
    """Send on every available channel; returns which went out and which failed (no secrets)."""
    sent: List[str] = []
    failed: Dict[str, str] = {}
    for name, send in channels().items():
        try:
            send(title, text)
            sent.append(name)
        except Exception as exc:
            failed[name] = f"{type(exc).__name__}: {exc}"[:200]
    return {"sent": sent, "failed": failed}


# ---- triggers ------------------------------------------------------------------------------

def _already_alerted(mission: Mission, kind: str) -> bool:
    last = mission.events[-1] if mission.events else {}
    return last.get("event") == "alerted" and last.get("kind") == kind and last.get("status") == mission.status


def after_run(store, mission_id: str) -> Optional[Dict[str, Any]]:
    """Called when a background run ends. Returns the alert recorded, if one was sent."""
    if not enabled():
        return None
    mission = store.load(mission_id)
    if mission is None or _already_alerted(mission, "status"):
        return None
    text = message(mission)
    if text is None:  # still working (max steps) or cancelled by the founder: nothing to tell
        return None
    result = notify(label(mission), f"The job {text}")
    mission.record("alerted", kind="status", status=mission.status, **result)
    store.save(mission)
    return result


def _last_activity(store, mission: Mission) -> datetime:
    times = [_parse(mission.updated_at)]
    try:
        lines = store.activity(mission.mission_id)[-1:]
        times += [_parse(line["at"]) for line in lines if line.get("at")]
    except Exception:
        pass
    return max(times)


def _parse(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


_QUIET_ALERTED: Dict[str, datetime] = {}  # mission -> the last activity we already alerted about


def check_stalled(store, is_running: Callable[[str], bool], now: Optional[datetime] = None) -> List[str]:
    """Alert once for each mission that should be working but has been quiet for STALL_MINUTES.
    It never saves the mission (a running one saves its own copy): the alert goes in the activity
    feed, which also restarts the quiet clock, so a mission still stuck alerts again 30 minutes on.
    Returns the ids alerted."""
    now = now or datetime.now(timezone.utc)
    alerted: List[str] = []
    for mission_id in store.list_ids():
        mission = store.load(mission_id)
        if mission is None or mission.status not in WORKING_STATUSES:
            _QUIET_ALERTED.pop(mission_id, None)
            continue
        last = _last_activity(store, mission)
        quiet = now - last
        if quiet < timedelta(minutes=STALL_MINUTES) or _QUIET_ALERTED.get(mission_id) == last:
            continue
        minutes, running = int(quiet.total_seconds() // 60), is_running(mission_id)
        if running:
            text = (f"has shown no progress for {minutes} minutes while {mission.status}. It may be stuck: "
                    "check its activity, and cancel and retry it if nothing moves.")
        else:
            text = f"is {mission.status} but nothing is running it (quiet for {minutes} minutes). Press Run to continue it."
        result = notify(label(mission), f"The job {text}")
        _QUIET_ALERTED[mission_id] = last
        try:
            store.record_activity(mission_id, "Watchdog", "status", f"no progress for {minutes} minutes"
                                  + ("" if running else " and not running") + f"; alerted ({', '.join(result['sent']) or 'failed'})")
        except Exception:
            pass
        alerted.append(mission_id)
    return alerted


_WATCHDOG: Dict[str, threading.Thread] = {}


def start_watchdog(store_factory: Callable[[], Any], is_running: Callable[[str], bool]) -> bool:
    """Check for stalled missions every WATCH_EVERY_SECONDS in a daemon thread (once per process)."""
    if not enabled() or "thread" in _WATCHDOG:
        return False
    stop = threading.Event()

    def watch() -> None:
        while not stop.wait(WATCH_EVERY_SECONDS):
            try:
                check_stalled(store_factory(), is_running)
            except Exception as exc:  # never let the watchdog die
                print(f"Orca watchdog: {type(exc).__name__}: {exc}")

    thread = threading.Thread(target=watch, name="orca-watchdog", daemon=True)
    _WATCHDOG["thread"] = thread
    thread.start()
    return True
