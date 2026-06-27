from __future__ import annotations

from typing import List

from app.platform.events.event import PlatformEvent
from app.platform.events.event_types import JOB_FAILED, VALIDATION_FAILED


def detect_anomalies(events: List[PlatformEvent]) -> List[str]:
    anomalies: List[str] = []
    job_failures = len([event for event in events if event.event_type == JOB_FAILED])
    validation_failures = len([event for event in events if event.event_type == VALIDATION_FAILED])
    if job_failures >= 2:
        anomalies.append("repeated_job_failures")
    if validation_failures >= 1:
        anomalies.append("validation_regression")
    return anomalies


def has_anomaly(events: List[PlatformEvent]) -> bool:
    return bool(detect_anomalies(events))
