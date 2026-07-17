from __future__ import annotations

from typing import Any, Iterable, Optional

from app.platform.company_brain.event_models import DomainEvent
from app.platform.company_brain.event_store import ImmutableEventStore
from app.platform.company_brain.knowledge_graph import KnowledgeGraphProjection
from app.platform.company_brain.memory import CompanyMemory


class CompanyBrain:
    """Read-only intelligence projection fed exclusively by production domain events."""

    def __init__(self, event_store: Optional[ImmutableEventStore] = None) -> None:
        self.event_store = event_store or ImmutableEventStore()
        self.knowledge_graph = KnowledgeGraphProjection()
        self.memory = CompanyMemory()

    def receive(self, event: DomainEvent) -> None:
        self.event_store.append(event)
        self.project(event)

    def project(self, event: DomainEvent) -> None:
        """Update read models for an event already owned by an event transport."""
        self.knowledge_graph.apply(event)
        self.memory.remember(event)

    def replay(self, events: Optional[Iterable[DomainEvent]] = None) -> dict[str, Any]:
        replay_events = list(events if events is not None else self.event_store.all())
        graph = KnowledgeGraphProjection()
        memory = CompanyMemory()
        for event in replay_events:
            graph.apply(event)
            memory.remember(event)
        return {"event_count": len(replay_events), "knowledge_graph": graph.snapshot(), "timeline": memory.timeline()}

    def timeline(self) -> list[dict[str, object]]:
        return self.memory.timeline()

    def mission_history(self, mission_id: str) -> list[dict[str, object]]:
        return self.memory.mission_history(mission_id)

    def projections(self) -> dict[str, Any]:
        return {"knowledge_graph": self.knowledge_graph.snapshot(), "timeline": self.timeline()}
