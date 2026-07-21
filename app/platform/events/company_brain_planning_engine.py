from __future__ import annotations

from typing import Iterable, Optional, Tuple

from app.platform.events.company_brain_models import CompanyBrainEntity
from app.platform.events.company_brain_reasoning_engine import CompanyBrainReasoningEngine
from app.platform.events.company_brain_reasoning_models import (
    ExecutionPlan,
    ExecutionSummary,
    PlanningAction,
    ReasoningFinding,
)


class CompanyBrainPlanningEngine:
    """Build deterministic execution plans from governed reasoning outputs."""

    def __init__(
        self,
        reasoning_engine: Optional[CompanyBrainReasoningEngine] = None,
    ) -> None:
        self._reasoning_engine = reasoning_engine or CompanyBrainReasoningEngine()

    def generate_execution_plan(self, mission_id: str) -> ExecutionPlan:
        normalized_id = _required(mission_id, "mission_id")
        summary = self._reasoning_engine.summarize_mission(normalized_id)
        blockers = _blockers(summary)
        actions = _actions(summary, blockers)
        return ExecutionPlan(
            mission=summary.mission,
            actions=actions,
            blockers=blockers,
            warnings=tuple(summary.warnings),
            supporting_event_ids=_supporting_event_ids(summary, actions, blockers),
            authoritative=summary.authoritative and not blockers,
        )


def _blockers(summary: ExecutionSummary) -> Tuple[ReasoningFinding, ...]:
    blockers = []
    mission_present = summary.mission.key in {entity.key for entity in summary.entities}
    if not mission_present:
        blockers.append(
            ReasoningFinding(
                code="MISSION_NOT_GOVERNED",
                title="Mission is not present in governed knowledge",
                description=(
                    "The mission must be projected into governed knowledge before "
                    "an authoritative execution plan can be produced."
                ),
                severity="error",
                supporting_event_ids=tuple(summary.supporting_event_ids),
                related_entities=(summary.mission,),
            )
        )
    if summary.entities and not summary.relationships:
        blockers.append(
            ReasoningFinding(
                code="DEPENDENCY_GRAPH_MISSING",
                title="Mission dependency graph is missing",
                description=(
                    "Governed relationships are required to sequence dependent work."
                ),
                severity="warning",
                supporting_event_ids=tuple(summary.supporting_event_ids),
                related_entities=(summary.mission,),
            )
        )
    return tuple(sorted(blockers, key=lambda item: item.code))


def _actions(
    summary: ExecutionSummary,
    blockers: Tuple[ReasoningFinding, ...],
) -> Tuple[PlanningAction, ...]:
    candidates = []
    sequence = 1

    for blocker in blockers:
        candidates.append(
            PlanningAction(
                sequence=sequence,
                code="RESOLVE_%s" % blocker.code,
                title="Resolve: %s" % blocker.title,
                description=blocker.description,
                priority="critical" if blocker.severity == "error" else "high",
                target_entities=blocker.related_entities,
                supporting_event_ids=blocker.supporting_event_ids,
            )
        )
        sequence += 1

    if not summary.evidence:
        candidates.append(
            PlanningAction(
                sequence=sequence,
                code="COLLECT_GOVERNED_EVIDENCE",
                title="Collect governed execution evidence",
                description=(
                    "Attach governed evidence or artifacts to support mission execution."
                ),
                priority="high",
                target_entities=(summary.mission,),
                supporting_event_ids=tuple(summary.supporting_event_ids),
            )
        )
        sequence += 1

    dependency_entities = _dependency_entities(summary)
    if dependency_entities:
        candidates.append(
            PlanningAction(
                sequence=sequence,
                code="EXECUTE_DEPENDENCY_SEQUENCE",
                title="Execute governed dependency sequence",
                description=(
                    "Process the governed mission dependencies in deterministic key order."
                ),
                priority="normal",
                target_entities=dependency_entities,
                supporting_event_ids=tuple(summary.supporting_event_ids),
            )
        )
        sequence += 1

    candidates.append(
        PlanningAction(
            sequence=sequence,
            code="VERIFY_MISSION_OUTCOME",
            title="Verify mission outcome",
            description=(
                "Rebuild the governed mission summary and verify evidence, relationships, "
                "and warnings after execution."
            ),
            priority="normal",
            target_entities=(summary.mission,),
            supporting_event_ids=tuple(summary.supporting_event_ids),
        )
    )
    return tuple(candidates)


def _dependency_entities(summary: ExecutionSummary) -> Tuple[CompanyBrainEntity, ...]:
    connected_keys = {
        key
        for relationship in summary.relationships
        for key in (relationship.source_key, relationship.target_key)
        if key != summary.mission.key
    }
    by_key = {entity.key: entity for entity in summary.entities}
    return tuple(by_key[key] for key in sorted(connected_keys) if key in by_key)


def _supporting_event_ids(
    summary: ExecutionSummary,
    actions: Tuple[PlanningAction, ...],
    blockers: Tuple[ReasoningFinding, ...],
) -> Tuple[str, ...]:
    values: Iterable[str] = (
        event_id
        for collection in (
            tuple(summary.supporting_event_ids),
            tuple(
                event_id
                for action in actions
                for event_id in action.supporting_event_ids
            ),
            tuple(
                event_id
                for blocker in blockers
                for event_id in blocker.supporting_event_ids
            ),
        )
        for event_id in collection
    )
    return tuple(dict.fromkeys(value for value in values if value))


def _required(value: str, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("%s is required" % name)
    return normalized
