from __future__ import annotations

from collections import deque
from typing import Dict, Iterable, Optional, Set, Tuple

from app.platform.events.company_brain_models import (
    CompanyBrainEntity,
    CompanyBrainExplanation,
    CompanyBrainRelationship,
)
from app.platform.events.company_brain_query_service import CompanyBrainQueryService
from app.platform.events.company_brain_reasoning_models import ImpactSummary


class CompanyBrainImpactAnalyzer:
    """Deterministic dependency impact analysis over Company Brain queries."""

    def __init__(
        self,
        query_service: Optional[CompanyBrainQueryService] = None,
    ) -> None:
        self._query_service = query_service or CompanyBrainQueryService()

    def analyze(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id: Optional[str] = None,
    ) -> ImpactSummary:
        subject = CompanyBrainEntity(
            _required(entity_type, "entity_type"),
            _required(entity_id, "entity_id"),
        )
        explanation = self._query_service.explain_entity(
            subject.authority,
            subject.entity_id,
            root_aggregate_type=root_aggregate_type,
            root_aggregate_id=root_aggregate_id,
        )
        entities = {entity.key: entity for entity in explanation.related_entities}
        entities[subject.key] = subject

        upstream_keys = {
            relationship.source_key
            for relationship in explanation.relationships
            if relationship.target_key == subject.key
        }
        downstream_keys = {
            relationship.target_key
            for relationship in explanation.relationships
            if relationship.source_key == subject.key
        }
        affected_keys = _reachable_downstream(
            subject.key,
            explanation.relationships,
        )

        upstream = _entities_for_keys(upstream_keys, entities)
        downstream = _entities_for_keys(downstream_keys, entities)
        affected = _entities_for_keys(affected_keys, entities)
        supporting_event_ids = _supporting_event_ids(
            subject.key,
            affected_keys,
            explanation,
        )

        return ImpactSummary(
            subject=subject,
            upstream=upstream,
            downstream=downstream,
            affected=affected,
            risk_score=_risk_score(upstream, downstream, affected),
            supporting_event_ids=supporting_event_ids,
            authoritative=explanation.authoritative,
        )


def _reachable_downstream(
    subject_key: str,
    relationships: Tuple[CompanyBrainRelationship, ...],
) -> Set[str]:
    adjacency: Dict[str, Set[str]] = {}
    for relationship in relationships:
        adjacency.setdefault(relationship.source_key, set()).add(relationship.target_key)

    visited: Set[str] = set()
    queue = deque(sorted(adjacency.get(subject_key, ())))
    while queue:
        key = queue.popleft()
        if key == subject_key or key in visited:
            continue
        visited.add(key)
        queue.extend(sorted(adjacency.get(key, ())))
    return visited


def _entities_for_keys(
    keys: Iterable[str],
    entities: Dict[str, CompanyBrainEntity],
) -> Tuple[CompanyBrainEntity, ...]:
    return tuple(entities[key] for key in sorted(set(keys)) if key in entities)


def _supporting_event_ids(
    subject_key: str,
    affected_keys: Set[str],
    explanation: CompanyBrainExplanation,
) -> Tuple[str, ...]:
    relevant_keys = set(affected_keys)
    relevant_keys.add(subject_key)
    relationship_event_ids = (
        event_id
        for relationship in sorted(explanation.relationships, key=_relationship_sort_key)
        if relationship.source_key in relevant_keys
        and relationship.target_key in relevant_keys
        for event_id in relationship.supporting_event_ids
    )
    return _ordered_unique(
        tuple(explanation.supporting_event_ids) + tuple(relationship_event_ids)
    )


def _risk_score(
    upstream: Tuple[CompanyBrainEntity, ...],
    downstream: Tuple[CompanyBrainEntity, ...],
    affected: Tuple[CompanyBrainEntity, ...],
) -> int:
    if not affected and not downstream:
        return 0
    score = 10
    score += min(len(upstream), 4) * 5
    score += min(len(downstream), 4) * 10
    score += min(len(affected), 6) * 10
    return min(score, 100)


def _relationship_sort_key(
    relationship: CompanyBrainRelationship,
) -> Tuple[str, str, str]:
    return (
        relationship.source_key,
        relationship.target_key,
        relationship.relationship,
    )


def _ordered_unique(values: Iterable[str]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _required(value: str, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("%s is required" % name)
    return normalized
