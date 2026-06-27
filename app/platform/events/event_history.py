from __future__ import annotations

from typing import List

from app.platform.events.event import PlatformEvent
from app.platform.events.event_bus import record_event


def append_event(history: List[PlatformEvent], event: PlatformEvent) -> List[PlatformEvent]:
    return record_event(history, event)


def latest_event(history: List[PlatformEvent]) -> PlatformEvent:
    return history[-1]
