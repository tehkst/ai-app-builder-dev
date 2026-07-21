from __future__ import annotations

from app.platform.events.company_brain_models import CompanyBrainEntity
from app.platform.events.company_brain_reasoning_engine import CompanyBrainReasoningEngine
from app.platform.events.company_brain_reasoning_models import (
    DecisionExplanation,
    ExecutionSummary,
    ImpactSummary,
    RootCauseSummary,
)


class _FakeExecutionSummaryService:
    def summarize_mission(self, mission_id: str) -> ExecutionSummary:
        assert mission_id == "mission-1"
        return ExecutionSummary(
            mission=CompanyBrainEntity("PlatformMission", mission_id),
            authoritative=True,
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
        _assert_entity_call(
            entity_type,
            entity_id,
            root_aggregate_type,
            root_aggregate_id,
        )
        return RootCauseSummary(
            failure=CompanyBrainEntity(entity_type, entity_id),
            likely_cause="governed cause",
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
        _assert_entity_call(
            entity_type,
            entity_id,
            root_aggregate_type,
            root_aggregate_id,
        )
        return ImpactSummary(
            subject=CompanyBrainEntity(entity_type, entity_id),
            risk_score=25,
            authoritative=True,
        )


class _FakeDecisionExplainer:
    def explain(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id=None,
    ) -> DecisionExplanation:
        _assert_entity_call(
            entity_type,
            entity_id,
            root_aggregate_type,
            root_aggregate_id,
        )
        return DecisionExplanation(
            decision=CompanyBrainEntity(entity_type, entity_id),
            reason="governed explanation",
            authoritative=True,
        )


class _UnusedQueryService:
    pass


def _assert_entity_call(
    entity_type: str,
    entity_id: str,
    root_aggregate_type: str,
    root_aggregate_id,
) -> None:
    assert entity_type == "PlatformDecision"
    assert entity_id == "decision-1"
    assert root_aggregate_type == "mission"
    assert root_aggregate_id == "mission-1"


def _engine() -> CompanyBrainReasoningEngine:
    return CompanyBrainReasoningEngine(
        query_service=_UnusedQueryService(),
        execution_summary_service=_FakeExecutionSummaryService(),
        root_cause_analyzer=_FakeRootCauseAnalyzer(),
        impact_analyzer=_FakeImpactAnalyzer(),
        decision_explainer=_FakeDecisionExplainer(),
    )


def _check_summary() -> None:
    summary = _engine().summarize_mission("mission-1")
    assert summary.mission.key == "PlatformMission:mission-1"
    assert summary.authoritative is True


def _check_root_cause() -> None:
    analysis = _engine().analyze_root_cause(
        "PlatformDecision",
        "decision-1",
        root_aggregate_id="mission-1",
    )
    assert analysis.failure.key == "PlatformDecision:decision-1"
    assert analysis.likely_cause == "governed cause"


def _check_impact() -> None:
    analysis = _engine().analyze_impact(
        "PlatformDecision",
        "decision-1",
        root_aggregate_id="mission-1",
    )
    assert analysis.subject.key == "PlatformDecision:decision-1"
    assert analysis.risk_score == 25


def _check_decision_explanation() -> None:
    explanation = _engine().explain_decision(
        "PlatformDecision",
        "decision-1",
        root_aggregate_id="mission-1",
    )
    assert explanation.decision.key == "PlatformDecision:decision-1"
    assert explanation.reason == "governed explanation"
    assert explanation.authoritative is True


def main() -> None:
    _check_summary()
    _check_root_cause()
    _check_impact()
    _check_decision_explanation()
    print("company brain reasoning engine: PASS")


if __name__ == "__main__":
    main()
