from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple

from app.platform.events.company_brain_models import (
    CompanyBrainEntity,
    CompanyBrainGraph,
    CompanyBrainRelationship,
)
from app.platform.events.company_brain_query_service import CompanyBrainQueryService
from app.platform.events.company_brain_reasoning_models import ReasoningFinding
from app.platform.events.company_brain_twin_models import (
    TWIN_ALIGNED,
    TWIN_MISSING,
    TWIN_UNEXPECTED,
    DigitalTwinSnapshot,
    TwinComponent,
)


class CompanyBrainTwinEngine:
    """Build and reconcile a governed digital twin from existing knowledge graphs.

    The twin is a read-only representation layer. It delegates governed topology
    retrieval to CompanyBrainQueryService and does not duplicate projection,
    reasoning, planning, execution, learning, or evolution behavior.
    """

    def __init__(self, query_service: Optional[CompanyBrainQueryService] = None) -> None:
        self._query_service = query_service or CompanyBrainQueryService()

    def build_snapshot(self, mission_id: str) -> DigitalTwinSnapshot:
        normalized_id = _required(mission_id, "mission_id")
        desired = self._query_service.get_mission_graph(normalized_id)
        mission = _mission_entity(desired, normalized_id)
        components = tuple(
            TwinComponent(entity=entity, desired=True, observed=False, status=TWIN_ALIGNED)
            for entity in sorted(desired.entities, key=lambda item: item.key)
        )
        warnings = () if desired.entities else ("No governed mission topology is available.",)
        authoritative = _desired_authoritative(desired, mission)
        return DigitalTwinSnapshot(
            mission=mission,
            desired_graph=desired,
            components=components,
            topology=_sorted_relationships(desired.relationships),
            warnings=warnings,
            supporting_event_ids=tuple(desired.supporting_event_ids),
            authoritative=authoritative,
        )

    def reconcile(
        self,
        mission_id: str,
        observed_graph: CompanyBrainGraph,
    ) -> DigitalTwinSnapshot:
        if not isinstance(observed_graph, CompanyBrainGraph):
            raise TypeError("observed_graph must be a CompanyBrainGraph")

        baseline = self.build_snapshot(mission_id)
        desired = baseline.desired_graph
        components = _components(desired, observed_graph)
        drift = _drift(desired, observed_graph, components)
        warnings = list(baseline.warnings)
        if not observed_graph.authoritative:
            warnings.append("Observed topology is not authoritative.")
        authoritative = (
            baseline.authoritative
            and observed_graph.authoritative
            and not any(item.severity == "error" for item in drift)
        )
        return DigitalTwinSnapshot(
            mission=baseline.mission,
            desired_graph=desired,
            observed_graph=observed_graph,
            components=components,
            topology=_merged_topology(desired, observed_graph),
            drift=drift,
            warnings=tuple(dict.fromkeys(warnings)),
            supporting_event_ids=_supporting_event_ids(desired, observed_graph, drift),
            authoritative=authoritative,
        )


def _mission_entity(graph: CompanyBrainGraph, mission_id: str) -> CompanyBrainEntity:
    candidates = tuple(
        entity
        for entity in graph.entities
        if entity.entity_id == mission_id and "mission" in entity.authority.lower()
    )
    if candidates:
        return sorted(candidates, key=lambda item: item.key)[0]
    return CompanyBrainEntity("PlatformMission", mission_id)


def _desired_authoritative(graph: CompanyBrainGraph, mission: CompanyBrainEntity) -> bool:
    return mission.key in {entity.key for entity in graph.entities} and bool(
        graph.supporting_event_ids
    )


def _components(
    desired: CompanyBrainGraph,
    observed: CompanyBrainGraph,
) -> Tuple[TwinComponent, ...]:
    desired_by_key: Dict[str, CompanyBrainEntity] = {
        entity.key: entity for entity in desired.entities
    }
    observed_by_key: Dict[str, CompanyBrainEntity] = {
        entity.key: entity for entity in observed.entities
    }
    values = []
    for key in sorted(set(desired_by_key) | set(observed_by_key)):
        in_desired = key in desired_by_key
        in_observed = key in observed_by_key
        status = (
            TWIN_ALIGNED
            if in_desired and in_observed
            else TWIN_MISSING
            if in_desired
            else TWIN_UNEXPECTED
        )
        values.append(
            TwinComponent(
                entity=desired_by_key.get(key) or observed_by_key[key],
                desired=in_desired,
                observed=in_observed,
                status=status,
            )
        )
    return tuple(values)


def _drift(
    desired: CompanyBrainGraph,
    observed: CompanyBrainGraph,
    components: Tuple[TwinComponent, ...],
) -> Tuple[ReasoningFinding, ...]:
    findings = []
    missing = tuple(item.entity for item in components if item.status == TWIN_MISSING)
    unexpected = tuple(item.entity for item in components if item.status == TWIN_UNEXPECTED)
    if missing:
        findings.append(
            ReasoningFinding(
                code="TWIN_COMPONENTS_MISSING",
                title="Desired components are missing from observed state",
                description="Observed state is missing: %s."
                % ", ".join(entity.key for entity in missing),
                severity="error",
                supporting_event_ids=tuple(desired.supporting_event_ids),
                related_entities=missing,
            )
        )
    if unexpected:
        findings.append(
            ReasoningFinding(
                code="TWIN_COMPONENTS_UNEXPECTED",
                title="Unexpected components exist in observed state",
                description="Observed state contains ungoverned components: %s."
                % ", ".join(entity.key for entity in unexpected),
                severity="error",
                supporting_event_ids=tuple(observed.supporting_event_ids),
                related_entities=unexpected,
            )
        )

    desired_edges = {_relationship_key(item) for item in desired.relationships}
    observed_edges = {_relationship_key(item) for item in observed.relationships}
    missing_edges = tuple(sorted(desired_edges - observed_edges))
    unexpected_edges = tuple(sorted(observed_edges - desired_edges))
    if missing_edges:
        findings.append(
            ReasoningFinding(
                code="TWIN_RELATIONSHIPS_MISSING",
                title="Desired relationships are missing from observed state",
                description="Observed topology is missing %s governed relationship(s)."
                % len(missing_edges),
                severity="warning",
                supporting_event_ids=tuple(desired.supporting_event_ids),
            )
        )
    if unexpected_edges:
        findings.append(
            ReasoningFinding(
                code="TWIN_RELATIONSHIPS_UNEXPECTED",
                title="Unexpected relationships exist in observed state",
                description="Observed topology contains %s ungoverned relationship(s)."
                % len(unexpected_edges),
                severity="warning",
                supporting_event_ids=tuple(observed.supporting_event_ids),
            )
        )
    return tuple(sorted(findings, key=lambda item: item.code))


def _relationship_key(item: CompanyBrainRelationship) -> Tuple[str, str, str]:
    return item.source_key, item.target_key, item.relationship


def _sorted_relationships(
    relationships: Tuple[CompanyBrainRelationship, ...],
) -> Tuple[CompanyBrainRelationship, ...]:
    return tuple(sorted(relationships, key=_relationship_key))


def _merged_topology(
    desired: CompanyBrainGraph,
    observed: CompanyBrainGraph,
) -> Tuple[CompanyBrainRelationship, ...]:
    by_key = {
        _relationship_key(item): item
        for item in tuple(desired.relationships) + tuple(observed.relationships)
    }
    return tuple(by_key[key] for key in sorted(by_key))


def _supporting_event_ids(
    desired: CompanyBrainGraph,
    observed: CompanyBrainGraph,
    drift: Tuple[ReasoningFinding, ...],
) -> Tuple[str, ...]:
    collections: Iterable[Tuple[str, ...]] = (
        tuple(desired.supporting_event_ids),
        tuple(observed.supporting_event_ids),
        *(tuple(item.supporting_event_ids) for item in drift),
    )
    return tuple(
        dict.fromkeys(
            event_id
            for collection in collections
            for event_id in collection
            if event_id
        )
    )


def _required(value: str, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("%s is required" % name)
    return normalized
