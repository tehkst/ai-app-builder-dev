from __future__ import annotations

from typing import Dict, List

from app.platform.events.event_types import JOB_FAILED, JOB_COMPLETED, VALIDATION_FAILED


SUBSCRIBERS: Dict[str, List[str]] = {
    JOB_FAILED: ["runtime_recovery", "engineering_memory", "event_metrics"],
    JOB_COMPLETED: ["engineering_memory", "event_metrics"],
    VALIDATION_FAILED: ["engineering_management", "event_metrics"],
}


def subscribers_for_event(event_type: str) -> List[str]:
    return list(SUBSCRIBERS.get(event_type, []))


def subscriber_registry() -> Dict[str, List[str]]:
    return {event_type: list(subscribers) for event_type, subscribers in SUBSCRIBERS.items()}
