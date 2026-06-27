from __future__ import annotations

from typing import Dict

from app.platform.events.event_types import ALL_EVENT_TYPES


def event_registry() -> Dict[str, Dict[str, object]]:
    return {
        event_type: {
            "event_type": event_type,
            "active": True,
        }
        for event_type in sorted(ALL_EVENT_TYPES)
    }


def registered_event_types() -> set:
    return set(event_registry())
