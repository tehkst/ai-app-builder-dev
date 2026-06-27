from __future__ import annotations

from typing import Dict, List

from app.platform.events.event import PlatformEvent


def event_metrics(events: List[PlatformEvent]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for event in events:
        counts[event.event_type] = counts.get(event.event_type, 0) + 1
    counts["event_count"] = len(events)
    return counts
