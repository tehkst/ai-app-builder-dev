"""Governed organizational event contracts and neutral emission boundary."""

from app.platform.events.event_models import OrganizationalEvent, build_organizational_event
from app.platform.events.event_sink import EventSink, NoOpEventSink, emit_organizational_event, reset_event_sink, set_event_sink

__all__ = [
    "OrganizationalEvent",
    "build_organizational_event",
    "EventSink",
    "NoOpEventSink",
    "emit_organizational_event",
    "reset_event_sink",
    "set_event_sink",
]
