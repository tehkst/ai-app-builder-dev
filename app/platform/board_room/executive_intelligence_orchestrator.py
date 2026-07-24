from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.platform.board_room.executive_perspective import (
    ExecutivePerspective,
    ExecutivePerspectiveSelector,
)
from app.platform.board_room.recommendation_generator import RecommendationGenerator


@dataclass(frozen=True)
class ExecutiveIntelligencePlan:
    """Read-only synthesis input assembled from existing intelligence owners."""

    strategy: str
    depth_tier: int
    perspective: ExecutivePerspective
    executive_brief: dict[str, Any]
    fallback_response: str

    @property
    def uses_decision_engine(self) -> bool:
        return bool(self.executive_brief)


class ExecutiveIntelligenceOrchestrator:
    """Selects reasoning depth and adapts the existing decision engine.

    This class owns no reasoning algorithm, state, action, or authority. The
    existing RecommendationGenerator and ExecutiveDecisionEngine remain the
    canonical substantive decision path.
    """

    _TIER_ZERO = {
        "direct_answer", "explanation", "architecture_explanation", "architecture_review",
        "status_request", "capability_query", "limitation_query",
        "capability_comparison", "competitive_comparison",
    }
    _STRATEGIES = {
        "direct_answer": "DIRECT_ANSWER",
        "explanation": "EXPLAIN",
        "brainstorming": "BRAINSTORM",
        "technical_diagnosis": "DIAGNOSE",
        "strategic_advice": "COMPARE",
        "executive_discussion": "PRIORITISE",
        "architecture_review": "ARCHITECTURE_REVIEW",
        "architecture_recommendation": "ARCHITECTURE_REVIEW",
        "product_review": "PRODUCT_REVIEW",
        "status_request": "GOVERNED_STATUS",
        "implementation_planning": "IMPLEMENTATION_DECISION",
        "implementation_handoff": "IMPLEMENTATION_DECISION",
        "mission_preparation": "IMPLEMENTATION_DECISION",
    }

    def __init__(self) -> None:
        self.recommendation_generator = RecommendationGenerator()

    def plan(
        self,
        founder_request: str,
        *,
        mode: str,
        context: dict[str, Any],
        decomposition: dict[str, Any] | None = None,
    ) -> ExecutiveIntelligencePlan:
        perspective = ExecutivePerspectiveSelector.select(founder_request)
        strategy = self._strategy(mode, decomposition or {})
        if mode in self._TIER_ZERO:
            return ExecutiveIntelligencePlan(strategy, 0, perspective, {}, "")

        reasoning = self.recommendation_generator.generate(
            founder_request,
            context,
            response_mode=mode,
            decomposition=decomposition,
        )
        strategy = self._resolved_strategy(strategy, reasoning)
        depth = self._depth(mode, perspective, founder_request)
        brief = self._brief(reasoning, strategy, perspective, depth)
        fallback = self._render_fallback(brief)
        return ExecutiveIntelligencePlan(strategy, depth, perspective, brief, fallback)

    @staticmethod
    def _resolved_strategy(default: str, reasoning: dict[str, Any]) -> str:
        decision = str(reasoning.get("decision_requested") or "")
        return {
            "choose between competing investments": "COMPARE",
            "diagnose the limiting constraint": "DIAGNOSE",
            "challenge the current direction": "CRITIQUE",
            "remove low-value work": "CRITIQUE",
            "sequence priorities over time": "ROADMAP",
            "evaluate architecture coherence": "ARCHITECTURE_REVIEW",
            "improve the founder product decision": "PRODUCT_REVIEW",
            "generate differentiated options": "BRAINSTORM",
            "decide whether the proposed change should proceed": "IMPLEMENTATION_DECISION",
        }.get(decision, default)

    @classmethod
    def _strategy(cls, mode: str, decomposition: dict[str, Any]) -> str:
        requested = str(decomposition.get("requested_action") or "")
        if requested == "COMPARE":
            return "COMPARE"
        if requested == "DIAGNOSE":
            return "DIAGNOSE"
        if requested == "PLAN":
            return "ROADMAP"
        if requested == "IMPLEMENT":
            return "IMPLEMENTATION_DECISION"
        if requested == "GOVERNED_ACTION":
            return "GOVERNED_STATUS"
        return cls._STRATEGIES.get(mode, "DIRECT_ANSWER")

    @staticmethod
    def _depth(mode: str, perspective: ExecutivePerspective, request: str) -> int:
        cross_functional = bool(perspective.supporting)
        material = any(
            term in request.lower()
            for term in (
                "fundrais", "runway", "market", "three months", "company strategy",
                "category", "architecture", "production", "capital", "trade-off",
            )
        )
        return 2 if cross_functional and material else 1

    @classmethod
    def _brief(
        cls,
        reasoning: dict[str, Any],
        strategy: str,
        perspective: ExecutivePerspective,
        depth: int,
    ) -> dict[str, Any]:
        recommendation = reasoning.get("recommendation") or {}
        alternatives = reasoning.get("alternatives") or []
        evidence = reasoning.get("evidence") or []
        uncertainty = reasoning.get("uncertainty") or []
        brief = {
            "objective": reasoning.get("intent"),
            "decision_type": reasoning.get("decision_requested"),
            "strategy": strategy,
            "verified_evidence": [
                {"fact": item.get("fact"), "source": item.get("source")}
                for item in evidence[:5]
                if isinstance(item, dict) and item.get("fact")
                and cls._evidence_relevant(str(item.get("fact")), strategy)
            ],
            "inferences": cls._inferences(reasoning),
            "unknowns": [
                str(item) for item in uncertainty[:4]
                if not str(item).lower().startswith("no material context gap")
            ],
            "options": [
                {
                    "name": item.get("option"),
                    "trade_off": item.get("trade_off"),
                    "criteria": item.get("criteria") or {},
                }
                for item in alternatives[:3]
                if isinstance(item, dict)
            ],
            "decisive_tradeoff": cls._decisive_tradeoff(alternatives),
            "recommended_position": recommendation.get("action"),
            "recommendation_rationale": recommendation.get("why"),
            "challenge_to_assumption": cls._challenge(reasoning),
            "founder_consequence": cls._founder_consequence(reasoning.get("impact")),
            "consequence_of_inaction": reasoning.get("consequence_of_inaction"),
            "risk": reasoning.get("risk") or {},
            "confidence": recommendation.get("confidence") or reasoning.get("confidence") or "medium",
            "perspective_contributions": cls._perspective_contributions(
                perspective, reasoning, depth
            ),
            "governance": {
                "read_only": True,
                "execution_allowed": False,
                "mission_creation_allowed": False,
            },
        }
        return brief

    @staticmethod
    def _evidence_relevant(fact: str, strategy: str) -> bool:
        lowered = fact.lower()
        if lowered.startswith("repository areas"):
            return strategy in {"ARCHITECTURE_REVIEW", "DIAGNOSE", "IMPLEMENTATION_DECISION"}
        if lowered.startswith(("active missions", "blocked missions")):
            return strategy in {"GOVERNED_STATUS", "DIAGNOSE", "IMPLEMENTATION_DECISION"}
        return True

    @staticmethod
    def _founder_consequence(value: Any) -> str:
        text = str(value or "").strip()
        return "" if text.lower().startswith("advances ") else text

    @staticmethod
    def _inferences(reasoning: dict[str, Any]) -> list[str]:
        recommendation = reasoning.get("recommendation") or {}
        rationale = str(recommendation.get("why") or "").strip()
        return [rationale] if rationale else []

    @staticmethod
    def _decisive_tradeoff(alternatives: list[dict[str, Any]]) -> str:
        if not alternatives:
            return "No credible alternative is established by the current evidence."
        first = alternatives[0]
        tradeoff = str(first.get("trade_off") or "").strip()
        if len(alternatives) == 1:
            return tradeoff or "The current evidence supports only one viable option."
        second = alternatives[1]
        return tradeoff or (
            f"Choosing {first.get('option')} prioritizes its leading criteria over "
            f"the specialist advantage of {second.get('option')}."
        )

    @staticmethod
    def _challenge(reasoning: dict[str, Any]) -> str:
        decision = str(reasoning.get("decision_requested") or "")
        consequence = str(reasoning.get("consequence_of_inaction") or "")
        if decision == "choose between competing investments":
            return "The apparent binary may be false if a smaller proof can preserve both strategic options."
        if decision in {"challenge the current direction", "remove low-value work"}:
            objective = str(reasoning.get("intent") or "the proposed rule").lower()
            return f"The premise treats {objective} as universally beneficial without proving the conditions where it holds. {consequence}".strip()
        if decision == "evaluate architecture coherence":
            return "A new abstraction is not progress if it creates a second owner for the same decision."
        return ""

    @staticmethod
    def _perspective_contributions(
        perspective: ExecutivePerspective,
        reasoning: dict[str, Any],
        depth: int,
    ) -> list[dict[str, str]]:
        if depth < 2:
            return []
        recommendation = reasoning.get("recommendation") or {}
        risk = reasoning.get("risk") or {}
        names = (perspective.primary, *perspective.supporting)[:3]
        return [
            {
                "perspective": name,
                "objective_interpretation": str(reasoning.get("intent") or ""),
                "primary_concern": " ".join(str(item) for item in (risk.get("factors") or [])[:2]),
                "recommended_position": str(recommendation.get("action") or ""),
                "tradeoff": ExecutiveIntelligenceOrchestrator._decisive_tradeoff(
                    reasoning.get("alternatives") or []
                ),
                "confidence": str(recommendation.get("confidence") or "medium"),
            }
            for name in names
        ]

    @staticmethod
    def _render_fallback(brief: dict[str, Any]) -> str:
        position = str(brief.get("recommended_position") or "Review the decision with more evidence.")
        rationale = str(brief.get("recommendation_rationale") or "")
        tradeoff = str(brief.get("decisive_tradeoff") or "")
        challenge = str(brief.get("challenge_to_assumption") or "")
        consequence = str(brief.get("founder_consequence") or "")
        evidence = brief.get("verified_evidence") or []
        facts = [
            str(item.get("fact"))
            for item in evidence[:2]
            if isinstance(item, dict) and item.get("fact")
        ]
        unknowns = [str(item) for item in (brief.get("unknowns") or [])[:2]]
        strategy = str(brief.get("strategy") or "")
        options = [
            str(item.get("name"))
            for item in (brief.get("options") or [])[:3]
            if isinstance(item, dict) and item.get("name")
        ]
        if strategy == "BRAINSTORM" and options:
            paragraphs = [
                "Three directions worth exploring:\n" + "\n".join(f"- {option}" for option in options)
            ]
        elif strategy == "DIAGNOSE":
            paragraphs = ["The most likely diagnosis is: " + position + "."]
        elif strategy == "CRITIQUE":
            paragraphs = ["I would challenge the premise: " + challenge, position + "."]
            challenge = ""
        elif strategy == "COMPARE":
            paragraphs = ["My position: " + position + "."]
        elif strategy == "ARCHITECTURE_REVIEW":
            paragraphs = ["The architectural choice I would make: " + position + "."]
        elif strategy == "PRODUCT_REVIEW":
            paragraphs = ["The product choice I would make: " + position + "."]
        else:
            paragraphs = [position.rstrip(".") + "."]
        if rationale and "strongest reversible path toward" not in rationale.lower():
            paragraphs.append(rationale)
        if facts:
            paragraphs.append("Verified evidence: " + "; ".join(facts) + ".")
        if tradeoff:
            paragraphs.append("The decisive trade-off: " + tradeoff.rstrip(".") + ".")
        if challenge:
            paragraphs.append("The assumption I would challenge: " + challenge)
        if consequence:
            paragraphs.append("For the company, this means: " + consequence)
        if unknowns:
            paragraphs.append("What remains unknown: " + "; ".join(unknowns))
        return "\n\n".join(paragraphs)
