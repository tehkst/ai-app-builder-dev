from __future__ import annotations

from typing import Optional

from app.platform.events.durable_store import DurableOrganizationalEventStore
from app.platform.events.knowledge_projection import (
    GovernedKnowledgeProjection,
    build_governed_knowledge_projection,
)


class AggregateKnowledgeProjectionService:
    """Build governed knowledge read models from durable aggregate event history."""

    def __init__(self, store: Optional[DurableOrganizationalEventStore] = None) -> None:
        self._store = store or DurableOrganizationalEventStore()

    def build_for_aggregate(
        self,
        aggregate_type: str,
        aggregate_id: str,
        *,
        limit: int = 100,
    ) -> GovernedKnowledgeProjection:
        normalized_type = str(aggregate_type or "").strip()
        normalized_id = str(aggregate_id or "").strip()
        if not normalized_type:
            raise ValueError("aggregate_type is required")
        if not normalized_id:
            raise ValueError("aggregate_id is required")

        events = self._store.list_for_aggregate(
            aggregate_type=normalized_type,
            aggregate_id=normalized_id,
            limit=limit,
        )
        return build_governed_knowledge_projection(events)


def build_projection_for_aggregate(
    aggregate_type: str,
    aggregate_id: str,
    *,
    limit: int = 100,
    store: Optional[DurableOrganizationalEventStore] = None,
) -> GovernedKnowledgeProjection:
    """Convenience boundary for Company Brain aggregate knowledge retrieval."""

    return AggregateKnowledgeProjectionService(store).build_for_aggregate(
        aggregate_type,
        aggregate_id,
        limit=limit,
    )
