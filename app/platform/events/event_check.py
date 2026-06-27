from __future__ import annotations

from app.platform.events.event import PlatformEvent
from app.platform.events.event_bus import filter_events, record_event
from app.platform.events.event_dispatcher import dispatch_event
from app.platform.events.event_history import append_event, latest_event
from app.platform.events.event_metrics import event_metrics
from app.platform.events.event_registry import registered_event_types
from app.platform.events.event_types import JOB_FAILED, JOB_COMPLETED, is_known_event_type
from app.platform.events.subscriber_registry import subscribers_for_event


def main() -> None:
    assert is_known_event_type(JOB_FAILED) is True
    assert JOB_FAILED in registered_event_types()
    assert subscribers_for_event(JOB_FAILED), JOB_FAILED

    event = PlatformEvent(
        event_id="event_check_1",
        event_type=JOB_FAILED,
        source="runtime",
        payload={"job_id": "job1"},
        created_at="2026-01-01T00:00:00Z",
    )
    history = record_event([], event)
    assert len(history) == 1, history
    assert filter_events(history, JOB_FAILED) == [event]

    completed = PlatformEvent(
        event_id="event_check_2",
        event_type=JOB_COMPLETED,
        source="runtime",
        payload={"job_id": "job2"},
        created_at="2026-01-01T00:00:01Z",
    )
    history = append_event(history, completed)
    assert latest_event(history) == completed

    dispatch = dispatch_event(event)
    assert dispatch["subscriber_count"] >= 1, dispatch

    metrics = event_metrics(history)
    assert metrics["event_count"] == 2, metrics
    assert metrics[JOB_FAILED] == 1, metrics

    print("EVENT BUS CHECK PASSED")


if __name__ == "__main__":
    main()
