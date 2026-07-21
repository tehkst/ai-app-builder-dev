from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from app.platform.events.company_brain_reasoning_models import (
    DecisionExplanation,
    ExecutionSummary,
    ImpactSummary,
    ReasoningFinding,
    RootCauseSummary,
)


@dataclass(frozen=True)
class MissionReasoningAssessment:
    """Governed mission-level synthesis of existing reasoning outputs."""

    summary: ExecutionSummary
    root_causes: Tuple[RootCauseSummary, ...] = field(default_factory=tuple)
    impacts: Tuple[ImpactSummary, ...] = field(default_factory=tuple)
    decisions: Tuple[DecisionExplanation, ...] = field(default_factory=tuple)
    unknowns: Tuple[ReasoningFinding, ...] = field(default_factory=tuple)
    assumptions: Tuple[ReasoningFinding, ...] = field(default_factory=tuple)
    risks: Tuple[ReasoningFinding, ...] = field(default_factory=tuple)
    recommended_strategy: str = ""
    next_best_action: str = ""
    confidence: float = 0.0
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    @property
    def mission(self):
        return self.summary.mission

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "mission": self.mission.as_dict(),
            "summary": self.summary.as_dict(),
            "root_causes": [item.as_dict() for item in self.root_causes],
            "impacts": [item.as_dict() for item in self.impacts],
            "decisions": [item.as_dict() for item in self.decisions],
            "unknowns": [item.as_dict() for item in self.unknowns],
            "assumptions": [item.as_dict() for item in self.assumptions],
            "risks": [item.as_dict() for item in self.risks],
            "recommended_strategy": self.recommended_strategy,
            "next_best_action": self.next_best_action,
            "confidence": self.confidence,
            "warnings": list(self.warnings),
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
        }
