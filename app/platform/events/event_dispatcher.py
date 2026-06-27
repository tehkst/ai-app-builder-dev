from __future__ import annotations

from typing import Dict, List

from app.platform.events.event import PlatformEvent
from app.platform.events.subscriber_registry import subscribers_for_event


def dispatch_event(event: PlatformEvent) -> Dict[str, object]:
    subscribers = subscribers_for_event(event.event_type)
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "subscriber_count": len(subscribers),
        "subscribers": subscribers,
    }


def dispatch_events(events: List[PlatformEvent]) -> List[Dict[str, object]]:
    return [dispatch_event(event) for event in events]
