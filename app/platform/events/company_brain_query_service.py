from __future__ import annotations

from collections import deque
from typing import Dict, Iterable, List, Optional, Set, Tuple

from app.platform.events.company_brain_models import (
    CompanyBrainEntity,
    CompanyBrainExplanation,
    CompanyBrainGraph,
    CompanyBrainRelationship,
)
from app.platform.events.cross_aggregate_knowledge_projection import (
    CrossAggregateKnowledgeProjectionService,
)
from app.platform.events.knowledge_projection import GovernedKnowledgeProjection


class CompanyBrainQueryService:
    """Stable read-only Company Brain boundary over governed projections."""

    def __init__(
        self,
        projection_service: Optional[CrossAggregateKnowledgeProjectionService] = None,
    ) -> None:
        self._projection_service = projection_service or CrossAggregateKnowledgeProjectionService()

    def get_mission_graph(self, mission_id: str) -> CompanyBrainGraph:
        projection = self._projection_service.build_from_aggregate("mission", mission_id)
        return _graph_from_projection(projection)

    def get_entity_lineage(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id: Optional[str] = None,
    ) -> CompanyBrainGraph:
        projection = self._projection_service.build_from_aggregate(
            root_aggregate_type,
            root_aggregate_id or entity_id,
        )
        key = _entity_key(entity_type, entity_id)
        return _connected_graph(projection, key)

    def find_supporting_evidence(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id: Optional[str] = None,
    ) -> Tuple[CompanyBrainEntity, ...]:
        graph = self.get_entity_lineage(
            entity_type,
            entity_id,
            root_aggregate_type=root_aggregate_type,
            root_aggregate_id=root_aggregate_id,
        )
        evidence = [
            entity
            for entity in graph.entities
            if entity.authority.endswith("Evidence")
            or entity.authority in {"PlatformWorkspaceArtifact", "PlatformExecutionEvidence"}
        ]
        return tuple(sorted(evidence, key=lambda item: item.key))

    def related_entities(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id: Optional[str] = None,
    ) -> Tuple[CompanyBrainEntity, ...]:
        projection = self._projection_service.build_from_aggregate(
            root_aggregate_type,
            root_aggregate_id or entity_id,
        )
        key = _entity_key(entity_type, entity_id)
        related_keys: Set[str] = set()
        for edge in projection.edges:
            if edge.source_key == key:
                related_keys.add(edge.target_key)
            if edge.target_key == key:
                related_keys.add(edge.source_key)
        entities = _entities_by_key(projection)
        return tuple(entities[item] for item in sorted(related_keys) if item in entities)

    def explain_entity(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id: Optional[str] = None,
    ) -> CompanyBrainExplanation:
        subject = CompanyBrainEntity(_required(entity_type, "entity_type"), _required(entity_id, "entity_id"))
        graph = self.get_entity_lineage(
            entity_type,
            entity_id,
            root_aggregate_type=root_aggregate_type,
            root_aggregate_id=root_aggregate_id,
        )
        related = tuple(entity for entity in graph.entities if entity.key != subject.key)
        return CompanyBrainExplanation(
            subject=subject,
            related_entities=related,
            relationships=graph.relationships,
            supporting_event_ids=graph.supporting_event_ids,
        )


def _graph_from_projection(projection: GovernedKnowledgeProjection) -> CompanyBrainGraph:
    relationships_by_key: Dict[Tuple[str, str, str], List[str]] = {}
    for edge in projection.edges:
        key = (edge.source_key, edge.target_key, edge.relationship)
        relationships_by_key.setdefault(key, []).append(edge.event_id)
    relationships = tuple(
        CompanyBrainRelationship(
            source_key=key[0],
            target_key=key[1],
            relationship=key[2],
            supporting_event_ids=tuple(dict.fromkeys(relationships_by_key[key])),
        )
        for key in sorted(relationships_by_key)
    )
    entities = tuple(
        CompanyBrainEntity(node.authority, node.entity_id)
        for node in projection.nodes
    )
    return CompanyBrainGraph(
        entities=entities,
        relationships=relationships,
        supporting_event_ids=projection.event_ids,
    )


def _connected_graph(projection: GovernedKnowledgeProjection, start_key: str) -> CompanyBrainGraph:
    entities = _entities_by_key(projection)
    if start_key not in entities:
        return CompanyBrainGraph()
    adjacency: Dict[str, Set[str]] = {}
    for edge in projection.edges:
        adjacency.setdefault(edge.source_key, set()).add(edge.target_key)
        adjacency.setdefault(edge.target_key, set()).add(edge.source_key)
    visited: Set[str] = set()
    queue = deque([start_key])
    while queue:
        key = queue.popleft()
        if key in visited:
            continue
        visited.add(key)
        queue.extend(sorted(adjacency.get(key, ())))
    filtered_edges = tuple(
        edge
        for edge in projection.edges
        if edge.source_key in visited and edge.target_key in visited
    )
    filtered = GovernedKnowledgeProjection(
        nodes=tuple(entities[key] for key in sorted(visited)),
        edges=filtered_edges,
        event_ids=tuple(
            dict.fromkeys(edge.event_id for edge in filtered_edges)
        ),
    )
    return _graph_from_projection(filtered)


def _entities_by_key(projection: GovernedKnowledgeProjection):
    return {node.key: node for node in projection.nodes}


def _entity_key(entity_type: str, entity_id: str) -> str:
    return "%s:%s" % (_required(entity_type, "entity_type"), _required(entity_id, "entity_id"))


def _required(value: str, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("%s is required" % name)
    return normalized
