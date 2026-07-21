from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple

from app.platform.events.company_brain_models import (
    CompanyBrainEntity,
    CompanyBrainExplanation,
    CompanyBrainRelationship,
)
from app.platform.events.company_brain_query_service import CompanyBrainQueryService
from app.platform.events.company_brain_reasoning_models import (
    ReasoningEvidence,
    ReasoningFinding,
    RootCauseSummary,
)


_EVIDENCE_AUTHORITIES = {
    "PlatformExecutionEvidence",
    "PlatformWorkspaceArtifact",
}


class CompanyBrainRootCauseAnalyzer:
    """Deterministic root-cause analysis over the Company Brain query boundary."""

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
    ) -> RootCauseSummary:
        failure = CompanyBrainEntity(
            _required(entity_type, "entity_type"),
            _required(entity_id, "entity_id"),
        )
        explanation = self._query_service.explain_entity(
            failure.authority,
            failure.entity_id,
            root_aggregate_type=root_aggregate_type,
            root_aggregate_id=root_aggregate_id,
        )
        entities = {entity.key: entity for entity in explanation.related_entities}
        entities[failure.key] = failure

        incoming = tuple(
            sorted(
                (
                    relationship
                    for relationship in explanation.relationships
                    if relationship.target_key == failure.key
                ),
                key=_relationship_sort_key,
            )
        )
        factors = tuple(
            _finding_for_relationship(relationship, entities)
            for relationship in incoming
        )
        evidence = _evidence_from_explanation(explanation)
        likely_cause = _likely_cause(incoming, entities)
        supporting_event_ids = _ordered_unique(
            tuple(explanation.supporting_event_ids)
            + tuple(
                event_id
                for relationship in incoming
                for event_id in relationship.supporting_event_ids
            )
        )

        return RootCauseSummary(
            failure=failure,
            contributing_factors=factors,
            evidence=evidence,
            likely_cause=likely_cause,
            confidence=_confidence(factors, evidence),
            supporting_event_ids=supporting_event_ids,
            authoritative=explanation.authoritative,
        )


def _finding_for_relationship(
    relationship: CompanyBrainRelationship,
    entities: Dict[str, CompanyBrainEntity],
) -> ReasoningFinding:
    source = entities.get(relationship.source_key)
    related = (source,) if source is not None else ()
    source_label = source.key if source is not None else relationship.source_key
    return ReasoningFinding(
        code="CONTRIBUTING_RELATIONSHIP",
        title="Contributing dependency",
        description="%s %s %s" % (
            source_label,
            relationship.relationship,
            relationship.target_key,
        ),
        severity="warning",
        supporting_event_ids=relationship.supporting_event_ids,
        related_entities=related,
    )


def _evidence_from_explanation(
    explanation: CompanyBrainExplanation,
) -> Tuple[ReasoningEvidence, ...]:
    evidence = []
    for entity in sorted(explanation.related_entities, key=lambda item: item.key):
        if not _is_evidence(entity):
            continue
        event_ids = _ordered_unique(
            event_id
            for relationship in explanation.relationships
            if relationship.source_key == entity.key or relationship.target_key == entity.key
            for event_id in relationship.supporting_event_ids
        )
        evidence.append(ReasoningEvidence(entity=entity, supporting_event_ids=event_ids))
    return tuple(evidence)


def _likely_cause(
    incoming: Tuple[CompanyBrainRelationship, ...],
    entities: Dict[str, CompanyBrainEntity],
) -> str:
    if not incoming:
        return "No governed contributing relationship was found."
    relationship = incoming[0]
    source = entities.get(relationship.source_key)
    source_label = source.key if source is not None else relationship.source_key
    return "%s via %s" % (source_label, relationship.relationship)


def _confidence(
    factors: Tuple[ReasoningFinding, ...],
    evidence: Tuple[ReasoningEvidence, ...],
) -> float:
    if not factors:
        return 0.0
    score = 0.5
    score += min(len(factors), 3) * 0.1
    score += min(len(evidence), 2) * 0.1
    return round(min(score, 0.9), 2)


def _is_evidence(entity: CompanyBrainEntity) -> bool:
    return entity.authority.endswith("Evidence") or entity.authority in _EVIDENCE_AUTHORITIES


def _relationship_sort_key(
    relationship: CompanyBrainRelationship,
) -> Tuple[str, str, str]:
    return (
        relationship.relationship,
        relationship.source_key,
        relationship.target_key,
    )


def _ordered_unique(values: Iterable[str]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _required(value: str, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("%s is required" % name)
    return normalized
