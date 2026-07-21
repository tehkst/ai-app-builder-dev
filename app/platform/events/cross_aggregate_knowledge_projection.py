from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional

from app.platform.events.durable_store import DurableOrganizationalEventStore
from app.platform.events.knowledge_projection import (
    GovernedKnowledgeProjection,
    build_governed_knowledge_projection,
)


class CrossAggregateKnowledgeProjectionService:
    """Build a unified governed graph across aggregates sharing a correlation boundary."""

    def __init__(self, store: Optional[DurableOrganizationalEventStore] = None) -> None:
        self._store = store or DurableOrganizationalEventStore()

    def build_from_aggregate(
        self,
        aggregate_type: str,
        aggregate_id: str,
        *,
        aggregate_limit: int = 100,
        correlation_limit: int = 500,
    ) -> GovernedKnowledgeProjection:
        normalized_type = str(aggregate_type or "").strip()
        normalized_id = str(aggregate_id or "").strip()
        if not normalized_type:
            raise ValueError("aggregate_type is required")
        if not normalized_id:
            raise ValueError("aggregate_id is required")

        root_events = self._store.list_for_aggregate(
            aggregate_type=normalized_type,
            aggregate_id=normalized_id,
            limit=aggregate_limit,
        )
        if not root_events:
            return build_governed_knowledge_projection(())

        events_by_id: Dict[str, Mapping[str, Any]] = {}
        correlation_ids = []
        for event in root_events:
            self._remember_event(events_by_id, event)
            correlation_id = str(event.get("correlation_id") or "").strip()
            if correlation_id:
                correlation_ids.append(correlation_id)

        for correlation_id in dict.fromkeys(correlation_ids):
            for event in self._store.list_for_correlation_id(
                correlation_id,
                limit=correlation_limit,
            ):
                self._remember_event(events_by_id, event)

        return build_governed_knowledge_projection(
            events_by_id[event_id] for event_id in sorted(events_by_id)
        )

    @staticmethod
    def _remember_event(
        events_by_id: Dict[str, Mapping[str, Any]],
        event: Mapping[str, Any],
    ) -> None:
        event_id = str(event.get("event_id") or "").strip()
        if event_id:
            events_by_id[event_id] = event


def build_cross_aggregate_projection(
    aggregate_type: str,
    aggregate_id: str,
    *,
    aggregate_limit: int = 100,
    correlation_limit: int = 500,
    store: Optional[DurableOrganizationalEventStore] = None,
) -> GovernedKnowledgeProjection:
    """Convenience boundary for mission-wide Company Brain lineage retrieval."""

    return CrossAggregateKnowledgeProjectionService(store).build_from_aggregate(
        aggregate_type,
        aggregate_id,
        aggregate_limit=aggregate_limit,
        correlation_limit=correlation_limit,
    )
