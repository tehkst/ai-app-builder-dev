from __future__ import annotations

from typing import Iterable, Optional, Tuple

from app.platform.events.company_brain_mission_reasoning_models import (
    MissionReasoningAssessment,
)
from app.platform.events.company_brain_reasoning_engine import CompanyBrainReasoningEngine
from app.platform.events.company_brain_reasoning_models import (
    DecisionExplanation,
    ExecutionSummary,
    ImpactSummary,
    ReasoningFinding,
    RootCauseSummary,
)


class CompanyBrainMissionReasoningEngine:
    """Synthesize governed mission reasoning without duplicating specialist analyzers."""

    def __init__(
        self,
        reasoning_engine: Optional[CompanyBrainReasoningEngine] = None,
    ) -> None:
        self._reasoning_engine = reasoning_engine or CompanyBrainReasoningEngine()

    def assess_mission(self, mission_id: str) -> MissionReasoningAssessment:
        normalized_id = _required(mission_id, "mission_id")
        summary = self._reasoning_engine.summarize_mission(normalized_id)
        root_causes = self._root_causes(summary)
        impacts = self._impacts(summary)
        decisions = self._decisions(summary)
        unknowns = _unknowns(summary, root_causes, impacts, decisions)
        assumptions = _assumptions(summary, root_causes, decisions)
        risks = _risks(summary, impacts)
        strategy, next_best_action = _strategy(
            summary,
            root_causes,
            decisions,
            unknowns,
            risks,
        )
        return MissionReasoningAssessment(
            summary=summary,
            root_causes=root_causes,
            impacts=impacts,
            decisions=decisions,
            unknowns=unknowns,
            assumptions=assumptions,
            risks=risks,
            recommended_strategy=strategy,
            next_best_action=next_best_action,
            confidence=_confidence(summary, root_causes, impacts, decisions, unknowns),
            warnings=tuple(summary.warnings),
            supporting_event_ids=_supporting_event_ids(
                summary,
                root_causes,
                impacts,
                decisions,
                unknowns,
                assumptions,
                risks,
            ),
            authoritative=_authoritative(
                summary,
                root_causes,
                impacts,
                decisions,
                unknowns,
            ),
        )

    def _root_causes(self, summary: ExecutionSummary) -> Tuple[RootCauseSummary, ...]:
        return tuple(
            self._reasoning_engine.analyze_root_cause(
                entity.authority,
                entity.entity_id,
                root_aggregate_id=summary.mission.entity_id,
            )
            for entity in _entities_matching(summary, ("failure", "error", "incident"))
        )

    def _impacts(self, summary: ExecutionSummary) -> Tuple[ImpactSummary, ...]:
        subjects = tuple(
            entity for entity in summary.entities if entity.key != summary.mission.key
        ) or (summary.mission,)
        return tuple(
            self._reasoning_engine.analyze_impact(
                entity.authority,
                entity.entity_id,
                root_aggregate_id=summary.mission.entity_id,
            )
            for entity in sorted(subjects, key=lambda item: item.key)
        )

    def _decisions(
        self,
        summary: ExecutionSummary,
    ) -> Tuple[DecisionExplanation, ...]:
        return tuple(
            self._reasoning_engine.explain_decision(
                entity.authority,
                entity.entity_id,
                root_aggregate_id=summary.mission.entity_id,
            )
            for entity in _entities_matching(summary, ("decision",))
        )


def _entities_matching(summary: ExecutionSummary, tokens: Tuple[str, ...]):
    return tuple(
        entity
        for entity in sorted(summary.entities, key=lambda item: item.key)
        if any(token in entity.authority.lower() for token in tokens)
    )


def _unknowns(
    summary: ExecutionSummary,
    root_causes: Tuple[RootCauseSummary, ...],
    impacts: Tuple[ImpactSummary, ...],
    decisions: Tuple[DecisionExplanation, ...],
) -> Tuple[ReasoningFinding, ...]:
    findings = []
    mission_present = summary.mission.key in {entity.key for entity in summary.entities}
    if not mission_present:
        findings.append(
            ReasoningFinding(
                code="MISSION_STATE_UNKNOWN",
                title="Mission state is not governed",
                description="The mission is absent from the governed execution summary.",
                severity="error",
                supporting_event_ids=tuple(summary.supporting_event_ids),
                related_entities=(summary.mission,),
            )
        )
    if not summary.evidence:
        findings.append(
            ReasoningFinding(
                code="MISSION_EVIDENCE_UNKNOWN",
                title="Mission evidence is incomplete",
                description="No governed evidence is available for mission-level reasoning.",
                severity="warning",
                supporting_event_ids=tuple(summary.supporting_event_ids),
                related_entities=(summary.mission,),
            )
        )
    if summary.entities and not summary.relationships:
        findings.append(
            ReasoningFinding(
                code="MISSION_DEPENDENCIES_UNKNOWN",
                title="Mission dependencies are unknown",
                description="Governed entities exist but no dependency relationships are available.",
                severity="warning",
                supporting_event_ids=tuple(summary.supporting_event_ids),
                related_entities=(summary.mission,),
            )
        )
    analyses = tuple(root_causes) + tuple(impacts) + tuple(decisions)
    if any(not item.authoritative for item in analyses):
        findings.append(
            ReasoningFinding(
                code="SPECIALIST_ANALYSIS_NOT_AUTHORITATIVE",
                title="Specialist analysis is not authoritative",
                description="At least one reused specialist reasoning result lacks governed authority.",
                severity="warning",
                supporting_event_ids=tuple(summary.supporting_event_ids),
                related_entities=(summary.mission,),
            )
        )
    return tuple(sorted(findings, key=lambda item: item.code))


def _assumptions(
    summary: ExecutionSummary,
    root_causes: Tuple[RootCauseSummary, ...],
    decisions: Tuple[DecisionExplanation, ...],
) -> Tuple[ReasoningFinding, ...]:
    findings = []
    if not root_causes:
        findings.append(
            ReasoningFinding(
                code="NO_FAILURE_ENTITY_OBSERVED",
                title="No failure entity is currently observed",
                description="Reasoning assumes no root-cause analysis is required until governed failure evidence appears.",
                severity="info",
                supporting_event_ids=tuple(summary.supporting_event_ids),
                related_entities=(summary.mission,),
            )
        )
    if not decisions:
        findings.append(
            ReasoningFinding(
                code="NO_DECISION_ENTITY_OBSERVED",
                title="No governed decision is currently observed",
                description="Reasoning assumes no decision explanation is required until a governed decision appears.",
                severity="info",
                supporting_event_ids=tuple(summary.supporting_event_ids),
                related_entities=(summary.mission,),
            )
        )
    return tuple(sorted(findings, key=lambda item: item.code))


def _risks(
    summary: ExecutionSummary,
    impacts: Tuple[ImpactSummary, ...],
) -> Tuple[ReasoningFinding, ...]:
    findings = []
    for impact in impacts:
        if impact.risk_score <= 0:
            continue
        severity = (
            "error"
            if impact.risk_score >= 75
            else "warning"
            if impact.risk_score >= 40
            else "info"
        )
        findings.append(
            ReasoningFinding(
                code="IMPACT_RISK_%s" % impact.subject.key.replace(":", "_").upper(),
                title="Governed impact risk identified",
                description="%s has deterministic impact risk score %s."
                % (impact.subject.key, impact.risk_score),
                severity=severity,
                supporting_event_ids=tuple(impact.supporting_event_ids),
                related_entities=(impact.subject,) + tuple(impact.affected),
            )
        )
    findings.extend(
        finding
        for finding in summary.findings
        if finding.severity in {"warning", "error"}
    )
    return tuple(sorted(findings, key=lambda item: item.code))


def _strategy(
    summary: ExecutionSummary,
    root_causes: Tuple[RootCauseSummary, ...],
    decisions: Tuple[DecisionExplanation, ...],
    unknowns: Tuple[ReasoningFinding, ...],
    risks: Tuple[ReasoningFinding, ...],
) -> Tuple[str, str]:
    if not summary.authoritative or any(item.severity == "error" for item in unknowns):
        return (
            "ESTABLISH_GOVERNED_MISSION_STATE",
            "Project the mission and its evidence into governed knowledge.",
        )
    if unknowns:
        return "CLOSE_GOVERNED_INFORMATION_GAPS", unknowns[0].description
    high_risks = tuple(item for item in risks if item.severity in {"warning", "error"})
    if high_risks:
        return "MITIGATE_HIGHEST_GOVERNED_RISK", high_risks[0].description
    if root_causes:
        return (
            "RESOLVE_GOVERNED_ROOT_CAUSE",
            root_causes[0].likely_cause or "Resolve the first governed root cause.",
        )
    if decisions:
        return (
            "VALIDATE_GOVERNED_DECISIONS",
            decisions[0].reason or "Validate the first governed decision.",
        )
    return (
        "PROCEED_TO_GOVERNED_PLANNING",
        "Generate a deterministic governed execution plan.",
    )


def _authoritative(
    summary: ExecutionSummary,
    root_causes: Tuple[RootCauseSummary, ...],
    impacts: Tuple[ImpactSummary, ...],
    decisions: Tuple[DecisionExplanation, ...],
    unknowns: Tuple[ReasoningFinding, ...],
) -> bool:
    analyses = tuple(root_causes) + tuple(impacts) + tuple(decisions)
    return (
        summary.authoritative
        and all(item.authoritative for item in analyses)
        and not any(item.severity == "error" for item in unknowns)
    )


def _confidence(
    summary: ExecutionSummary,
    root_causes: Tuple[RootCauseSummary, ...],
    impacts: Tuple[ImpactSummary, ...],
    decisions: Tuple[DecisionExplanation, ...],
    unknowns: Tuple[ReasoningFinding, ...],
) -> float:
    score = 0.4 if summary.authoritative else 0.0
    score += 0.2 if summary.evidence else 0.0
    score += 0.15 if summary.relationships else 0.0
    analyses = tuple(root_causes) + tuple(impacts) + tuple(decisions)
    score += 0.25 if all(item.authoritative for item in analyses) else 0.0
    score -= 0.1 * sum(1 for item in unknowns if item.severity == "warning")
    score -= 0.25 * sum(1 for item in unknowns if item.severity == "error")
    return round(max(0.0, min(1.0, score)), 2)


def _supporting_event_ids(
    summary: ExecutionSummary,
    root_causes: Tuple[RootCauseSummary, ...],
    impacts: Tuple[ImpactSummary, ...],
    decisions: Tuple[DecisionExplanation, ...],
    unknowns: Tuple[ReasoningFinding, ...],
    assumptions: Tuple[ReasoningFinding, ...],
    risks: Tuple[ReasoningFinding, ...],
) -> Tuple[str, ...]:
    collections: Iterable[Tuple[str, ...]] = (
        tuple(summary.supporting_event_ids),
        *(tuple(item.supporting_event_ids) for item in root_causes),
        *(tuple(item.supporting_event_ids) for item in impacts),
        *(tuple(item.supporting_event_ids) for item in decisions),
        *(tuple(item.supporting_event_ids) for item in unknowns),
        *(tuple(item.supporting_event_ids) for item in assumptions),
        *(tuple(item.supporting_event_ids) for item in risks),
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
