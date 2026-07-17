from __future__ import annotations

from typing import Iterable

from app.platform.company_brain.event_models import DomainEvent
from app.platform.digital_twin.twin_event_handlers import apply_domain_event
from app.platform.digital_twin.twin_state import TwinState


def rebuild_twin(events: Iterable[DomainEvent]) -> TwinState:
    state = TwinState()
    for event in events:
        apply_domain_event(state, event)
    return state
