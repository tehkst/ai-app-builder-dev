from __future__ import annotations

import logging
from threading import RLock
from typing import Any, Mapping, Optional, Protocol


class EventSink(Protocol):
    """Neutral outbound event boundary owned by the production platform."""

    def emit(
        self, event_type: str, *, source: str, aggregate_type: str, aggregate_id: str,
        correlation_id: Optional[str] = None, causation_id: Optional[str] = None,
        actor: str = "system", payload: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        ...


class NoOpEventSink:
    def emit(
        self, event_type: str, *, source: str, aggregate_type: str, aggregate_id: str,
        correlation_id: Optional[str] = None, causation_id: Optional[str] = None,
        actor: str = "system", payload: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        return None


_lock = RLock()
_event_sink: EventSink = NoOpEventSink()
logger = logging.getLogger(__name__)


def set_event_sink(event_sink: EventSink) -> None:
    global _event_sink
    with _lock:
        _event_sink = event_sink


def reset_event_sink() -> None:
    set_event_sink(NoOpEventSink())


def emit_domain_event(
    event_type: str, *, source: str, aggregate_type: str, aggregate_id: str,
    correlation_id: Optional[str] = None, causation_id: Optional[str] = None,
    actor: str = "system", payload: Optional[Mapping[str, Any]] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> None:
    with _lock:
        event_sink = _event_sink
    try:
        event_sink.emit(
            event_type, source=source, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
            correlation_id=correlation_id, causation_id=causation_id, actor=actor,
            payload=payload, metadata=metadata,
        )
    except Exception as exc:
        logger.warning("event_sink_emit_failed event_type=%s error=%s", event_type, type(exc).__name__)
