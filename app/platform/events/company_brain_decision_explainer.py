from __future__ import annotations

from typing import Iterable, Optional, Tuple

from app.platform.events.company_brain_impact_analyzer import (
    CompanyBrainImpactAnalyzer,
)
from app.platform.events.company_brain_models import CompanyBrainEntity
from app.platform.events.company_brain_query_service import CompanyBrainQueryService
from app.platform.events.company_brain_reasoning_models import (
    DecisionExplanation,
    ImpactSummary,
    RootCauseSummary,
)
from app.platform.events.company_brain_root_cause_analyzer import (
    CompanyBrainRootCauseAnalyzer,
)


class CompanyBrainDecisionExplainer:
    """Compose deterministic Company Brain analyses into a decision explanation."""

    def __init__(
        self,
        query_service: Optional[CompanyBrainQueryService] = None,
        root_cause_analyzer: Optional[CompanyBrainRootCauseAnalyzer] = None,
        impact_analyzer: Optional[CompanyBrainImpactAnalyzer] = None,
    ) -> None:
        service = query_service or CompanyBrainQueryService()
        self._root_cause_analyzer = root_cause_analyzer or CompanyBrainRootCauseAnalyzer(
            service
        )
        self._impact_analyzer = impact_analyzer or CompanyBrainImpactAnalyzer(service)

    def explain(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id: Optional[str] = None,
    ) -> DecisionExplanation:
        decision = CompanyBrainEntity(
            _required(entity_type, "entity_type"),
            _required(entity_id, "entity_id"),
        )
        root_cause = self._root_cause_analyzer.analyze(
            decision.authority,
            decision.entity_id,
            root_aggregate_type=root_aggregate_type,
            root_aggregate_id=root_aggregate_id,
        )
        impact = self._impact_analyzer.analyze(
            decision.authority,
            decision.entity_id,
            root_aggregate_type=root_aggregate_type,
            root_aggregate_id=root_aggregate_id,
        )

        dependencies = _dependencies(root_cause, impact)
        supporting_event_ids = _ordered_unique(
            tuple(root_cause.supporting_event_ids)
            + tuple(impact.supporting_event_ids)
        )

        return DecisionExplanation(
            decision=decision,
            reason=_reason(root_cause, impact),
            evidence=root_cause.evidence,
            dependencies=dependencies,
            affected_systems=impact.affected,
            supporting_event_ids=supporting_event_ids,
            authoritative=root_cause.authoritative and impact.authoritative,
        )


def _dependencies(
    root_cause: RootCauseSummary,
    impact: ImpactSummary,
) -> Tuple[CompanyBrainEntity, ...]:
    candidates = list(impact.upstream)
    for finding in root_cause.contributing_factors:
        candidates.extend(finding.related_entities)
    by_key = {entity.key: entity for entity in candidates}
    return tuple(by_key[key] for key in sorted(by_key))


def _reason(root_cause: RootCauseSummary, impact: ImpactSummary) -> str:
    cause = root_cause.likely_cause or "No governed cause was identified."
    if impact.affected:
        return "%s; the governed downstream impact includes %d entities with risk score %d." % (
            cause,
            len(impact.affected),
            impact.risk_score,
        )
    return "%s; no governed downstream impact was identified." % cause


def _ordered_unique(values: Iterable[str]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _required(value: str, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("%s is required" % name)
    return normalized
