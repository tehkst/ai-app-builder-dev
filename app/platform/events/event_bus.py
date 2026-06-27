from __future__ import annotations

from typing import List

from app.platform.events.event import PlatformEvent


def record_event(events: List[PlatformEvent], event: PlatformEvent) -> List[PlatformEvent]:
    return events + [event]


def filter_events(events: List[PlatformEvent], event_type: str) -> List[PlatformEvent]:
    return [event for event in events if event.event_type == event_type]
