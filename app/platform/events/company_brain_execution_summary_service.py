from __future__ import annotations

from typing import Dict, Iterable, Optional, Set, Tuple

from app.platform.events.company_brain_models import (
    CompanyBrainEntity,
    CompanyBrainGraph,
    CompanyBrainRelationship,
)
from app.platform.events.company_brain_query_service import CompanyBrainQueryService
from app.platform.events.company_brain_reasoning_models import (
    ExecutionSummary,
    ReasoningEvidence,
    ReasoningFinding,
)


class CompanyBrainExecutionSummaryService:
    """Build deterministic mission summaries through the public Company Brain API."""

    def __init__(self, brain: Optional[CompanyBrainQueryService] = None) -> None:
        self._brain = brain or CompanyBrainQueryService()

    def summarize_mission(self, mission_id: str) -> ExecutionSummary:
        normalized_id = _required(mission_id, "mission_id")
        graph = self._brain.get_mission_graph(normalized_id)
        mission = _mission_entity(graph, normalized_id)
        evidence = _evidence_from_graph(graph)
        warnings = _warnings_for_graph(graph, mission, evidence)
        findings = _findings_for_graph(graph, mission, evidence, warnings)
        return ExecutionSummary(
            mission=mission,
            entities=tuple(sorted(graph.entities, key=lambda entity: entity.key)),
            relationships=tuple(
                sorted(
                    graph.relationships,
                    key=lambda relationship: (
                        relationship.source_key,
                        relationship.target_key,
                        relationship.relationship,
                    ),
                )
            ),
            evidence=evidence,
            findings=findings,
            warnings=warnings,
            supporting_event_ids=tuple(dict.fromkeys(graph.supporting_event_ids)),
        )


def _mission_entity(graph: CompanyBrainGraph, mission_id: str) -> CompanyBrainEntity:
    exact = [
        entity
        for entity in graph.entities
        if entity.entity_id == mission_id and entity.authority.lower().endswith("mission")
    ]
    if exact:
        return sorted(exact, key=lambda entity: entity.key)[0]
    matching = [entity for entity in graph.entities if entity.entity_id == mission_id]
    if matching:
        return sorted(matching, key=lambda entity: entity.key)[0]
    return CompanyBrainEntity("PlatformMission", mission_id)


def _evidence_from_graph(graph: CompanyBrainGraph) -> Tuple[ReasoningEvidence, ...]:
    event_ids_by_entity: Dict[str, Set[str]] = {}
    for relationship in graph.relationships:
        for key in (relationship.source_key, relationship.target_key):
            event_ids_by_entity.setdefault(key, set()).update(relationship.supporting_event_ids)
    evidence = []
    for entity in graph.entities:
        if _is_evidence(entity):
            evidence.append(
                ReasoningEvidence(
                    entity=entity,
                    supporting_event_ids=tuple(sorted(event_ids_by_entity.get(entity.key, ()))),
                )
            )
    return tuple(sorted(evidence, key=lambda item: item.entity.key))


def _findings_for_graph(
    graph: CompanyBrainGraph,
    mission: CompanyBrainEntity,
    evidence: Tuple[ReasoningEvidence, ...],
    warnings: Tuple[str, ...],
) -> Tuple[ReasoningFinding, ...]:
    findings = [
        ReasoningFinding(
            code="MISSION_GRAPH_SUMMARY",
            title="Mission execution graph available",
            description=(
                "Mission %s is connected to %d entities through %d governed relationships."
                % (mission.entity_id, len(graph.entities), len(graph.relationships))
            ),
            supporting_event_ids=tuple(dict.fromkeys(graph.supporting_event_ids)),
            related_entities=tuple(sorted(graph.entities, key=lambda entity: entity.key)),
        )
    ]
    if evidence:
        findings.append(
            ReasoningFinding(
                code="SUPPORTING_EVIDENCE_PRESENT",
                title="Supporting evidence present",
                description="%d governed evidence entities support the mission graph." % len(evidence),
                supporting_event_ids=_event_ids_from_evidence(evidence),
                related_entities=tuple(item.entity for item in evidence),
            )
        )
    if warnings:
        findings.append(
            ReasoningFinding(
                code="EXECUTION_SUMMARY_WARNING",
                title="Execution summary requires attention",
                description="; ".join(warnings),
                severity="warning",
                supporting_event_ids=tuple(dict.fromkeys(graph.supporting_event_ids)),
                related_entities=(mission,),
            )
        )
    return tuple(findings)


def _warnings_for_graph(
    graph: CompanyBrainGraph,
    mission: CompanyBrainEntity,
    evidence: Tuple[ReasoningEvidence, ...],
) -> Tuple[str, ...]:
    warnings = []
    if not graph.entities:
        warnings.append("No governed entities were found for the mission.")
    elif mission.key not in {entity.key for entity in graph.entities}:
        warnings.append("The mission entity was not present in the governed graph.")
    if graph.entities and not graph.relationships:
        warnings.append("The mission graph contains no governed relationships.")
    if graph.entities and not evidence:
        warnings.append("No supporting evidence entities were found.")
    return tuple(warnings)


def _event_ids_from_evidence(evidence: Iterable[ReasoningEvidence]) -> Tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            event_id
            for item in evidence
            for event_id in item.supporting_event_ids
        )
    )


def _is_evidence(entity: CompanyBrainEntity) -> bool:
    authority = entity.authority.lower()
    return authority.endswith("evidence") or authority.endswith("artifact")


def _required(value: str, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("%s is required" % name)
    return normalized
