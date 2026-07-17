from __future__ import annotations

from typing import Protocol

from app.platform.company_brain.event_models import DomainEvent


class EventSubscriber(Protocol):
    def handle(self, event: DomainEvent) -> None:
        ...


class RecordingSubscriber:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def handle(self, event: DomainEvent) -> None:
        self.events.append(event)
