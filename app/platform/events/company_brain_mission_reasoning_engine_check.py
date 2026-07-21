from __future__ import annotations

from app.platform.events.company_brain_mission_reasoning_engine import (
    CompanyBrainMissionReasoningEngine,
)
from app.platform.events.company_brain_models import (
    CompanyBrainEntity,
    CompanyBrainRelationship,
)
from app.platform.events.company_brain_reasoning_models import (
    DecisionExplanation,
    ExecutionSummary,
    ImpactSummary,
    ReasoningEvidence,
    RootCauseSummary,
)


class _FakeReasoningEngine:
    def __init__(self, summary: ExecutionSummary) -> None:
        self.summary = summary
        self.calls = []

    def summarize_mission(self, mission_id: str) -> ExecutionSummary:
        self.calls.append(("summary", mission_id))
        return self.summary

    def analyze_root_cause(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id=None,
    ) -> RootCauseSummary:
        self.calls.append(("root", entity_type, entity_id, root_aggregate_id))
        return RootCauseSummary(
            failure=CompanyBrainEntity(entity_type, entity_id),
            likely_cause="governed dependency failure",
            confidence=0.9,
            supporting_event_ids=("event-root",),
            authoritative=True,
        )

    def analyze_impact(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id=None,
    ) -> ImpactSummary:
        self.calls.append(("impact", entity_type, entity_id, root_aggregate_id))
        score = 60 if entity_type == "PlatformFailure" else 10
        return ImpactSummary(
            subject=CompanyBrainEntity(entity_type, entity_id),
            risk_score=score,
            supporting_event_ids=("event-impact",),
            authoritative=True,
        )

    def explain_decision(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id=None,
    ) -> DecisionExplanation:
        self.calls.append(("decision", entity_type, entity_id, root_aggregate_id))
        return DecisionExplanation(
            decision=CompanyBrainEntity(entity_type, entity_id),
            reason="governed decision reason",
            supporting_event_ids=("event-decision",),
            authoritative=True,
        )


def _governed_summary() -> ExecutionSummary:
    mission = CompanyBrainEntity("PlatformMission", "mission-1")
    failure = CompanyBrainEntity("PlatformFailure", "failure-1")
    decision = CompanyBrainEntity("PlatformDecision", "decision-1")
    evidence = ReasoningEvidence(mission, ("event-1",))
    return ExecutionSummary(
        mission=mission,
        entities=(mission, failure, decision),
        relationships=(
            CompanyBrainRelationship(
                source_key=mission.key,
                target_key=failure.key,
                relationship="contains",
                supporting_event_ids=("event-1",),
            ),
        ),
        evidence=(evidence,),
        supporting_event_ids=("event-1",),
        authoritative=True,
    )


def _check_composition_without_duplication() -> None:
    fake = _FakeReasoningEngine(_governed_summary())
    assessment = CompanyBrainMissionReasoningEngine(fake).assess_mission("mission-1")

    assert fake.calls == [
        ("summary", "mission-1"),
        ("root", "PlatformFailure", "failure-1", "mission-1"),
        ("impact", "PlatformDecision", "decision-1", "mission-1"),
        ("impact", "PlatformFailure", "failure-1", "mission-1"),
        ("decision", "PlatformDecision", "decision-1", "mission-1"),
    ]
    assert assessment.summary is fake.summary
    assert assessment.root_causes[0].likely_cause == "governed dependency failure"
    assert assessment.decisions[0].reason == "governed decision reason"
    assert assessment.recommended_strategy == "MITIGATE_HIGHEST_GOVERNED_RISK"
    assert assessment.next_best_action.endswith("risk score 60.")
    assert assessment.confidence == 1.0
    assert assessment.authoritative is True
    assert assessment.supporting_event_ids == (
        "event-1",
        "event-root",
        "event-impact",
        "event-decision",
    )

    serialized = assessment.as_dict()
    assert serialized["mission"]["entity_id"] == "mission-1"
    assert serialized["summary"]["authoritative"] is True
    assert serialized["root_causes"][0]["confidence"] == 0.9
    assert serialized["recommended_strategy"] == "MITIGATE_HIGHEST_GOVERNED_RISK"


def _check_unknown_mission_state() -> None:
    mission = CompanyBrainEntity("PlatformMission", "mission-2")
    fake = _FakeReasoningEngine(
        ExecutionSummary(
            mission=mission,
            authoritative=False,
        )
    )
    assessment = CompanyBrainMissionReasoningEngine(fake).assess_mission("mission-2")

    assert tuple(item.code for item in assessment.unknowns) == (
        "MISSION_EVIDENCE_UNKNOWN",
        "MISSION_STATE_UNKNOWN",
    )
    assert assessment.recommended_strategy == "ESTABLISH_GOVERNED_MISSION_STATE"
    assert assessment.authoritative is False
    assert assessment.confidence == 0.0
    assert fake.calls == [
        ("summary", "mission-2"),
        ("impact", "PlatformMission", "mission-2", "mission-2"),
    ]


def _check_non_authoritative_specialist_result() -> None:
    class _NonAuthoritativeImpact(_FakeReasoningEngine):
        def analyze_impact(self, entity_type, entity_id, **kwargs):
            return ImpactSummary(
                subject=CompanyBrainEntity(entity_type, entity_id),
                authoritative=False,
            )

    fake = _NonAuthoritativeImpact(_governed_summary())
    assessment = CompanyBrainMissionReasoningEngine(fake).assess_mission("mission-1")

    assert "SPECIALIST_ANALYSIS_NOT_AUTHORITATIVE" in {
        item.code for item in assessment.unknowns
    }
    assert assessment.authoritative is False
    assert assessment.confidence == 0.65


def _check_no_failure_or_decision_assumptions() -> None:
    mission = CompanyBrainEntity("PlatformMission", "mission-3")
    workflow = CompanyBrainEntity("PlatformWorkflowRun", "workflow-1")
    summary = ExecutionSummary(
        mission=mission,
        entities=(mission, workflow),
        relationships=(
            CompanyBrainRelationship(
                source_key=mission.key,
                target_key=workflow.key,
                relationship="contains",
                supporting_event_ids=("event-3",),
            ),
        ),
        evidence=(ReasoningEvidence(mission, ("event-3",)),),
        supporting_event_ids=("event-3",),
        authoritative=True,
    )
    assessment = CompanyBrainMissionReasoningEngine(
        _FakeReasoningEngine(summary)
    ).assess_mission("mission-3")

    assert tuple(item.code for item in assessment.assumptions) == (
        "NO_DECISION_ENTITY_OBSERVED",
        "NO_FAILURE_ENTITY_OBSERVED",
    )
    assert assessment.recommended_strategy == "PROCEED_TO_GOVERNED_PLANNING"
    assert assessment.authoritative is True


def _check_validation() -> None:
    engine = CompanyBrainMissionReasoningEngine(_FakeReasoningEngine(_governed_summary()))
    try:
        engine.assess_mission(" ")
    except ValueError as error:
        assert str(error) == "mission_id is required"
    else:
        raise AssertionError("blank mission_id must fail")


def main() -> None:
    _check_composition_without_duplication()
    _check_unknown_mission_state()
    _check_non_authoritative_specialist_result()
    _check_no_failure_or_decision_assumptions()
    _check_validation()
    print("company brain mission reasoning engine: PASS")


if __name__ == "__main__":
    main()
