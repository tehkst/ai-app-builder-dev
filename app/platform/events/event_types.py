from __future__ import annotations

JOB_CREATED = "job.created"
JOB_QUEUED = "job.queued"
JOB_ASSIGNED = "job.assigned"
JOB_STARTED = "job.started"
JOB_COMPLETED = "job.completed"
JOB_FAILED = "job.failed"
JOB_RECOVERED = "job.recovered"
VALIDATION_PASSED = "validation.passed"
VALIDATION_FAILED = "validation.failed"

RUNTIME_EVENTS = {
    JOB_CREATED,
    JOB_QUEUED,
    JOB_ASSIGNED,
    JOB_STARTED,
    JOB_COMPLETED,
    JOB_FAILED,
    JOB_RECOVERED,
}

VALIDATION_EVENTS = {VALIDATION_PASSED, VALIDATION_FAILED}
ALL_EVENT_TYPES = RUNTIME_EVENTS | VALIDATION_EVENTS


def is_known_event_type(event_type: str) -> bool:
    return event_type in ALL_EVENT_TYPES
