from __future__ import annotations

import os
from typing import Any, Mapping, Optional

from app.platform.company_brain.event_bus import InProcessEventBus
from app.platform.company_brain.company_brain import CompanyBrain
from app.platform.company_brain.event_models import DomainEvent, create_domain_event
from app.platform.company_brain.event_store import ImmutableEventStore


EVENTS_ENABLED_ENV = "COMPANY_BRAIN_EVENTS_ENABLED"
EVENT_STORE = ImmutableEventStore()
EVENT_BUS = InProcessEventBus()
COMPANY_BRAIN = CompanyBrain(EVENT_STORE)
EVENT_BUS.subscribe("*", COMPANY_BRAIN.project)


def events_enabled() -> bool:
    return os.getenv(EVENTS_ENABLED_ENV, "false").strip().lower() in {"1", "true", "yes", "on"}


def publish_domain_event(
    event_type: str, *, source: str, aggregate_type: str, aggregate_id: str,
    correlation_id: Optional[str] = None, causation_id: Optional[str] = None,
    actor: str = "system", payload: Optional[Mapping[str, Any]] = None,
    metadata: Optional[Mapping[str, Any]] = None, enabled: Optional[bool] = None,
) -> Optional[DomainEvent]:
    if not (events_enabled() if enabled is None else enabled):
        return None
    event = create_domain_event(
        event_type, source=source, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        correlation_id=correlation_id, causation_id=causation_id, actor=actor,
        payload=payload, metadata=metadata,
    )
    EVENT_STORE.append(event)
    EVENT_BUS.publish(event)
    return event
