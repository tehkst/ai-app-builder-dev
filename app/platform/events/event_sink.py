from __future__ import annotations

import logging
from threading import RLock
from typing import Protocol

from app.platform.events.event_models import OrganizationalEvent


logger = logging.getLogger(__name__)


class EventSink(Protocol):
    """Neutral outbound boundary for non-authoritative organizational events."""

    def emit(self, event: OrganizationalEvent) -> None:
        ...


class NoOpEventSink:
    def emit(self, event: OrganizationalEvent) -> None:
        return None


_lock = RLock()
_event_sink: EventSink = NoOpEventSink()


def set_event_sink(event_sink: EventSink) -> None:
    global _event_sink
    with _lock:
        _event_sink = event_sink


def reset_event_sink() -> None:
    set_event_sink(NoOpEventSink())


def emit_organizational_event(event: OrganizationalEvent) -> None:
    """Emit after canonical persistence; sink failures never invert platform authority."""

    with _lock:
        event_sink = _event_sink
    try:
        event_sink.emit(event)
    except Exception as exc:
        logger.warning(
            "organizational_event_emit_failed event_type=%s event_id=%s error=%s",
            event.event_type,
            event.event_id,
            type(exc).__name__,
        )
