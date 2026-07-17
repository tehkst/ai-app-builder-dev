from __future__ import annotations

from typing import Any, Mapping, Optional

from app.platform.company_brain.event_publisher import publish_domain_event


class CompanyBrainEventSink:
    """Application adapter from the neutral production event boundary."""

    def emit(
        self, event_type: str, *, source: str, aggregate_type: str, aggregate_id: str,
        correlation_id: Optional[str] = None, causation_id: Optional[str] = None,
        actor: str = "system", payload: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        publish_domain_event(
            event_type, source=source, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
            correlation_id=correlation_id, causation_id=causation_id, actor=actor,
            payload=payload, metadata=metadata, enabled=True,
        )
