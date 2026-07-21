from __future__ import annotations

from app.platform.events.company_brain_models import (
    CompanyBrainEntity,
    CompanyBrainRelationship,
)
from app.platform.events.company_brain_planning_engine import CompanyBrainPlanningEngine
from app.platform.events.company_brain_reasoning_models import (
    ExecutionSummary,
    ReasoningEvidence,
)


class _FakeReasoningEngine:
    def __init__(self, summary: ExecutionSummary) -> None:
        self._summary = summary
        self.calls = []

    def summarize_mission(self, mission_id: str) -> ExecutionSummary:
        self.calls.append(mission_id)
        return self._summary


def _governed_summary() -> ExecutionSummary:
    mission = CompanyBrainEntity("PlatformMission", "mission-1")
    workflow = CompanyBrainEntity("PlatformWorkflowRun", "workflow-1")
    artifact = CompanyBrainEntity("PlatformWorkspaceArtifact", "artifact-1")
    evidence = CompanyBrainEntity("PlatformExecutionEvidence", "evidence-1")
    return ExecutionSummary(
        mission=mission,
        entities=(artifact, evidence, mission, workflow),
        relationships=(
            CompanyBrainRelationship(
                source_key=mission.key,
                target_key=workflow.key,
                relationship="started",
                supporting_event_ids=("event-1",),
            ),
            CompanyBrainRelationship(
                source_key=workflow.key,
                target_key=artifact.key,
                relationship="produced",
                supporting_event_ids=("event-2",),
            ),
        ),
        evidence=(
            ReasoningEvidence(
                entity=evidence,
                supporting_event_ids=("event-3",),
            ),
        ),
        supporting_event_ids=("event-1", "event-2", "event-3"),
        authoritative=True,
    )


def _check_governed_plan() -> None:
    reasoning = _FakeReasoningEngine(_governed_summary())
    plan = CompanyBrainPlanningEngine(reasoning).generate_execution_plan("mission-1")

    assert reasoning.calls == ["mission-1"]
    assert plan.mission.key == "PlatformMission:mission-1"
    assert plan.blockers == ()
    assert tuple(action.code for action in plan.actions) == (
        "EXECUTE_DEPENDENCY_SEQUENCE",
        "VERIFY_MISSION_OUTCOME",
    )
    assert tuple(
        entity.key for entity in plan.actions[0].target_entities
    ) == (
        "PlatformWorkflowRun:workflow-1",
        "PlatformWorkspaceArtifact:artifact-1",
    )
    assert plan.supporting_event_ids == ("event-1", "event-2", "event-3")
    assert plan.authoritative is True
    serialized = plan.as_dict()
    assert serialized["mission"]["entity_id"] == "mission-1"
    assert serialized["actions"][0]["sequence"] == 1


def _check_gap_plan() -> None:
    mission = CompanyBrainEntity("PlatformMission", "mission-2")
    summary = ExecutionSummary(
        mission=mission,
        entities=(),
        warnings=("No governed entities were found for the mission.",),
        supporting_event_ids=("event-gap",),
        authoritative=False,
    )
    plan = CompanyBrainPlanningEngine(
        _FakeReasoningEngine(summary)
    ).generate_execution_plan("mission-2")

    assert tuple(blocker.code for blocker in plan.blockers) == (
        "MISSION_NOT_GOVERNED",
    )
    assert tuple(action.code for action in plan.actions) == (
        "RESOLVE_MISSION_NOT_GOVERNED",
        "COLLECT_GOVERNED_EVIDENCE",
        "VERIFY_MISSION_OUTCOME",
    )
    assert plan.actions[0].priority == "critical"
    assert plan.warnings == (
        "No governed entities were found for the mission.",
    )
    assert plan.authoritative is False


def _check_missing_relationships() -> None:
    mission = CompanyBrainEntity("PlatformMission", "mission-3")
    summary = ExecutionSummary(
        mission=mission,
        entities=(mission,),
        evidence=(
            ReasoningEvidence(
                entity=CompanyBrainEntity("PlatformExecutionEvidence", "evidence-3")
            ),
        ),
        authoritative=True,
    )
    plan = CompanyBrainPlanningEngine(
        _FakeReasoningEngine(summary)
    ).generate_execution_plan("mission-3")
    assert tuple(blocker.code for blocker in plan.blockers) == (
        "DEPENDENCY_GRAPH_MISSING",
    )
    assert plan.actions[0].code == "RESOLVE_DEPENDENCY_GRAPH_MISSING"
    assert plan.actions[0].priority == "high"
    assert plan.authoritative is False


def _check_validation() -> None:
    engine = CompanyBrainPlanningEngine(_FakeReasoningEngine(_governed_summary()))
    try:
        engine.generate_execution_plan(" ")
    except ValueError as error:
        assert str(error) == "mission_id is required"
    else:
        raise AssertionError("blank mission_id must fail")


def main() -> None:
    _check_governed_plan()
    _check_gap_plan()
    _check_missing_relationships()
    _check_validation()
    print("company brain planning engine: PASS")


if __name__ == "__main__":
    main()
