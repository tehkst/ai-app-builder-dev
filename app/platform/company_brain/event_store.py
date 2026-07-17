from __future__ import annotations

from threading import RLock
from typing import Optional

from app.platform.company_brain.event_models import DomainEvent


class ImmutableEventStore:
    """Append-only in-process foundation; future adapters may replace its storage transport."""

    def __init__(self) -> None:
        self._events: list[DomainEvent] = []
        self._by_id: dict[str, DomainEvent] = {}
        self._lock = RLock()

    def append(self, event: DomainEvent) -> DomainEvent:
        with self._lock:
            if event.event_id in self._by_id:
                raise ValueError("domain event IDs are immutable and unique")
            self._events.append(event)
            self._by_id[event.event_id] = event
        return event

    def get(self, event_id: str) -> Optional[DomainEvent]:
        return self._by_id.get(event_id)

    def all(self) -> list[DomainEvent]:
        return list(self._events)

    def for_aggregate(self, aggregate_type: str, aggregate_id: str) -> list[DomainEvent]:
        return [event for event in self._events if event.aggregate_type == aggregate_type and event.aggregate_id == aggregate_id]

    def after(self, event_id: Optional[str] = None) -> list[DomainEvent]:
        if not event_id:
            return self.all()
        for index, event in enumerate(self._events):
            if event.event_id == event_id:
                return list(self._events[index + 1:])
        return []
