from __future__ import annotations

from app.platform.events.company_brain_decision_explainer import (
    CompanyBrainDecisionExplainer,
)
from app.platform.events.company_brain_models import CompanyBrainEntity
from app.platform.events.company_brain_reasoning_models import (
    ImpactSummary,
    ReasoningEvidence,
    ReasoningFinding,
    RootCauseSummary,
)


class _FakeRootCauseAnalyzer:
    def analyze(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id=None,
    ) -> RootCauseSummary:
        assert entity_type == "PlatformDecision"
        assert entity_id == "decision-1"
        assert root_aggregate_type == "mission"
        assert root_aggregate_id == "mission-1"
        dependency = CompanyBrainEntity("PlatformWorkflowRun", "workflow-1")
        evidence = CompanyBrainEntity("PlatformExecutionEvidence", "evidence-1")
        return RootCauseSummary(
            failure=CompanyBrainEntity(entity_type, entity_id),
            contributing_factors=(
                ReasoningFinding(
                    code="CONTRIBUTING_RELATIONSHIP",
                    title="Contributing dependency",
                    description="workflow dependency",
                    severity="warning",
                    supporting_event_ids=("event-1",),
                    related_entities=(dependency,),
                ),
            ),
            evidence=(
                ReasoningEvidence(
                    entity=evidence,
                    supporting_event_ids=("event-2",),
                ),
            ),
            likely_cause="PlatformWorkflowRun:workflow-1 via produced",
            confidence=0.7,
            supporting_event_ids=("event-1", "event-2"),
            authoritative=True,
        )


class _FakeImpactAnalyzer:
    def analyze(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id=None,
    ) -> ImpactSummary:
        assert entity_type == "PlatformDecision"
        assert entity_id == "decision-1"
        assert root_aggregate_type == "mission"
        assert root_aggregate_id == "mission-1"
        dependency = CompanyBrainEntity("PlatformWorkflowRun", "workflow-1")
        affected = CompanyBrainEntity("PlatformWorkspaceArtifact", "artifact-1")
        return ImpactSummary(
            subject=CompanyBrainEntity(entity_type, entity_id),
            upstream=(dependency,),
            downstream=(affected,),
            affected=(affected,),
            risk_score=35,
            supporting_event_ids=("event-2", "event-3"),
            authoritative=True,
        )


class _UnusedQueryService:
    pass


def _check_explanation() -> None:
    explainer = CompanyBrainDecisionExplainer(
        query_service=_UnusedQueryService(),
        root_cause_analyzer=_FakeRootCauseAnalyzer(),
        impact_analyzer=_FakeImpactAnalyzer(),
    )
    explanation = explainer.explain(
        "PlatformDecision",
        "decision-1",
        root_aggregate_id="mission-1",
    )

    assert explanation.decision.key == "PlatformDecision:decision-1"
    assert explanation.reason == (
        "PlatformWorkflowRun:workflow-1 via produced; the governed downstream "
        "impact includes 1 entities with risk score 35."
    )
    assert tuple(entity.key for entity in explanation.dependencies) == (
        "PlatformWorkflowRun:workflow-1",
    )
    assert tuple(entity.key for entity in explanation.affected_systems) == (
        "PlatformWorkspaceArtifact:artifact-1",
    )
    assert tuple(item.entity.key for item in explanation.evidence) == (
        "PlatformExecutionEvidence:evidence-1",
    )
    assert explanation.supporting_event_ids == (
        "event-1",
        "event-2",
        "event-3",
    )
    assert explanation.authoritative is True
    assert explanation.as_dict()["decision"]["entity_id"] == "decision-1"


def _check_no_downstream_impact() -> None:
    class EmptyImpactAnalyzer(_FakeImpactAnalyzer):
        def analyze(self, entity_type: str, entity_id: str, **kwargs) -> ImpactSummary:
            return ImpactSummary(subject=CompanyBrainEntity(entity_type, entity_id))

    explanation = CompanyBrainDecisionExplainer(
        query_service=_UnusedQueryService(),
        root_cause_analyzer=_FakeRootCauseAnalyzer(),
        impact_analyzer=EmptyImpactAnalyzer(),
    ).explain(
        "PlatformDecision",
        "decision-1",
        root_aggregate_id="mission-1",
    )
    assert explanation.reason.endswith("no governed downstream impact was identified.")
    assert explanation.authoritative is False


def _check_validation() -> None:
    explainer = CompanyBrainDecisionExplainer(
        query_service=_UnusedQueryService(),
        root_cause_analyzer=_FakeRootCauseAnalyzer(),
        impact_analyzer=_FakeImpactAnalyzer(),
    )
    try:
        explainer.explain(" ", "decision-1")
    except ValueError as error:
        assert str(error) == "entity_type is required"
    else:
        raise AssertionError("blank entity_type must fail")


def main() -> None:
    _check_explanation()
    _check_no_downstream_impact()
    _check_validation()
    print("decision explainer: PASS")


if __name__ == "__main__":
    main()
