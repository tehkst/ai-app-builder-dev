from __future__ import annotations

from typing import Optional

from app.platform.events.company_brain_decision_explainer import (
    CompanyBrainDecisionExplainer,
)
from app.platform.events.company_brain_execution_summary_service import (
    CompanyBrainExecutionSummaryService,
)
from app.platform.events.company_brain_impact_analyzer import CompanyBrainImpactAnalyzer
from app.platform.events.company_brain_query_service import CompanyBrainQueryService
from app.platform.events.company_brain_reasoning_models import (
    DecisionExplanation,
    ExecutionSummary,
    ImpactSummary,
    RootCauseSummary,
)
from app.platform.events.company_brain_root_cause_analyzer import (
    CompanyBrainRootCauseAnalyzer,
)


class CompanyBrainReasoningEngine:
    """Stable facade for deterministic Company Brain reasoning capabilities."""

    def __init__(
        self,
        query_service: Optional[CompanyBrainQueryService] = None,
        execution_summary_service: Optional[CompanyBrainExecutionSummaryService] = None,
        root_cause_analyzer: Optional[CompanyBrainRootCauseAnalyzer] = None,
        impact_analyzer: Optional[CompanyBrainImpactAnalyzer] = None,
        decision_explainer: Optional[CompanyBrainDecisionExplainer] = None,
    ) -> None:
        service = query_service or CompanyBrainQueryService()
        self._execution_summary_service = (
            execution_summary_service or CompanyBrainExecutionSummaryService(service)
        )
        self._root_cause_analyzer = root_cause_analyzer or CompanyBrainRootCauseAnalyzer(
            service
        )
        self._impact_analyzer = impact_analyzer or CompanyBrainImpactAnalyzer(service)
        self._decision_explainer = decision_explainer or CompanyBrainDecisionExplainer(
            service,
            root_cause_analyzer=self._root_cause_analyzer,
            impact_analyzer=self._impact_analyzer,
        )

    def summarize_mission(self, mission_id: str) -> ExecutionSummary:
        return self._execution_summary_service.summarize_mission(mission_id)

    def analyze_root_cause(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id: Optional[str] = None,
    ) -> RootCauseSummary:
        return self._root_cause_analyzer.analyze(
            entity_type,
            entity_id,
            root_aggregate_type=root_aggregate_type,
            root_aggregate_id=root_aggregate_id,
        )

    def analyze_impact(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id: Optional[str] = None,
    ) -> ImpactSummary:
        return self._impact_analyzer.analyze(
            entity_type,
            entity_id,
            root_aggregate_type=root_aggregate_type,
            root_aggregate_id=root_aggregate_id,
        )

    def explain_decision(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id: Optional[str] = None,
    ) -> DecisionExplanation:
        return self._decision_explainer.explain(
            entity_type,
            entity_id,
            root_aggregate_type=root_aggregate_type,
            root_aggregate_id=root_aggregate_id,
        )
