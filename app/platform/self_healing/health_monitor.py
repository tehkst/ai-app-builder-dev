from __future__ import annotations

from typing import Dict, List

from app.platform.events.event import PlatformEvent
from app.platform.events.event_types import JOB_FAILED, JOB_COMPLETED


def health_summary(events: List[PlatformEvent]) -> Dict[str, int]:
    failed = len([event for event in events if event.event_type == JOB_FAILED])
    completed = len([event for event in events if event.event_type == JOB_COMPLETED])
    return {
        "event_count": len(events),
        "failed_job_events": failed,
        "completed_job_events": completed,
    }


def health_status(events: List[PlatformEvent]) -> str:
    summary = health_summary(events)
    if summary["failed_job_events"] > summary["completed_job_events"]:
        return "degraded"
    return "healthy"
