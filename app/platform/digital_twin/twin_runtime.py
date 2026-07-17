from __future__ import annotations

from typing import Iterable

from app.platform.company_brain.event_models import DomainEvent
from app.platform.digital_twin.twin_event_handlers import apply_domain_event
from app.platform.digital_twin.twin_projection import rebuild_twin
from app.platform.digital_twin.twin_state import TwinState


class DigitalTwin:
    """Eventually consistent projection. It has no production write dependency."""

    def __init__(self) -> None:
        self.state = TwinState()

    def handle(self, event: DomainEvent) -> None:
        apply_domain_event(self.state, event)

    def replay(self, events: Iterable[DomainEvent]) -> TwinState:
        self.state = rebuild_twin(events)
        return self.state

    def snapshot(self) -> dict[str, object]:
        return self.state.snapshot()
