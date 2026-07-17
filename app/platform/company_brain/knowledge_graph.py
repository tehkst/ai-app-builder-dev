from __future__ import annotations

from typing import Any

from app.platform.company_brain.event_models import DomainEvent


class KnowledgeGraphProjection:
    def __init__(self) -> None:
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, str]] = []

    def apply(self, event: DomainEvent) -> None:
        key = "{}:{}".format(event.aggregate_type, event.aggregate_id)
        self._nodes[key] = {
            "id": key, "aggregate_type": event.aggregate_type, "aggregate_id": event.aggregate_id,
            "latest_event_type": event.event_type, "updated_at": event.timestamp,
        }
        causation = event.causation_id
        if causation:
            self._edges.append({"from": causation, "to": event.event_id, "relationship": "caused"})

    def snapshot(self) -> dict[str, Any]:
        return {"nodes": list(self._nodes.values()), "edges": list(self._edges)}
