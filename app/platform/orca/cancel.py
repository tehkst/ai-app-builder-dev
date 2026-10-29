"""Founder cancellations of running missions. A request is a flag the running mission sees at its
next step and in its next AI call (the employee then stops like an outage, using up no attempt);
a command already running in the sandbox finishes first. Missions that aren't running are
cancelled straight away by `Orca.cancel_mission`."""
from __future__ import annotations

import threading
from typing import Dict

from app.platform.runtime.ai_provider import AIProviderError

_REQUESTED: Dict[str, str] = {}  # mission_id -> who cancelled it
_LOCK = threading.Lock()


class MissionCancelled(AIProviderError):
    """Raised from an employee's chat call once the founder cancelled the mission. An AIProviderError
    so the agent loop ends the employee's run like an outage (no attempt used, no bug logged)."""


def request(mission_id: str, decided_by: str = "founder") -> None:
    with _LOCK:
        _REQUESTED[mission_id] = decided_by


def requested_by(mission_id: str) -> str:
    with _LOCK:
        return _REQUESTED.get(mission_id, "founder")


def requested(mission_id: str) -> bool:
    with _LOCK:
        return mission_id in _REQUESTED


def stoppable(mission_id: str, chat):
    """`chat`, refusing to start another AI call once the mission is cancelled."""
    def call(messages, tools):
        if requested(mission_id):
            raise MissionCancelled("The founder cancelled this mission.")
        return chat(messages, tools)
    return call


def clear(mission_id: str) -> None:
    with _LOCK:
        _REQUESTED.pop(mission_id, None)
