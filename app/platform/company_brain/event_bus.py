from __future__ import annotations

from threading import RLock
from typing import Callable

from app.platform.company_brain.event_models import DomainEvent


EventHandler = Callable[[DomainEvent], None]


class InProcessEventBus:
    """Production publishes outward; subscribers never write back into production."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = {}
        self._lock = RLock()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        with self._lock:
            handlers = self._subscribers.setdefault(event_type, [])
            if handler not in handlers:
                handlers.append(handler)

    def publish(self, event: DomainEvent) -> list[str]:
        with self._lock:
            handlers = list(self._subscribers.get(event.event_type, [])) + list(self._subscribers.get("*", []))
        failures = []
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                failures.append(type(exc).__name__)
        return failures
