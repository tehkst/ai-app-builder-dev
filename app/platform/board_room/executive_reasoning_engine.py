from __future__ import annotations

from typing import Any

from app.platform.board_room.context_retriever import ContextRetriever
from app.platform.board_room.recommendation_generator import RecommendationGenerator
from app.platform.board_room.response_presenter import ResponsePresenter


class ExecutiveReasoningEngine:
    """Runs the read-only executive reasoning pipeline before Board Room action."""

    def __init__(self) -> None:
        self.context_retriever = ContextRetriever()
        self.recommendation_generator = RecommendationGenerator()
        self.response_presenter = ResponsePresenter()

    def reason(self, founder_request: str, *, response_mode: str) -> dict[str, Any]:
        lightweight = response_mode in {"casual", "clarify"}
        context = self.context_retriever.retrieve(founder_request, lightweight=lightweight)
        reasoning = self.recommendation_generator.generate(
            founder_request,
            context,
            response_mode=response_mode,
        )
        return {
            "reasoning": reasoning,
            "founder_response": self.response_presenter.present(reasoning),
            "context": context,
            "technical_details": reasoning.get("technical_details") or {},
        }

    @staticmethod
    def build_ai_guidance(result: dict[str, Any]) -> str:
        reasoning = result.get("reasoning") or {}
        recommendation = reasoning.get("recommendation") or {}
        alternatives = reasoning.get("alternatives") or []
        risk = reasoning.get("risk") or {}
        criteria = reasoning.get("evaluation_criteria") or []
        evidence = reasoning.get("evidence") or []
        uncertainty = reasoning.get("uncertainty") or []
        presentation_mode = reasoning.get("presentation_mode") or "prioritization"
        return "\n".join(
            [
                "Lead with the recommendation and use concise business language.",
                f"Presentation mode: {presentation_mode}",
                f"Founder intent: {reasoning.get('intent', 'evaluate the request')}",
                f"Business context: {reasoning.get('business_context', '')}",
                f"Company memory: {reasoning.get('company_memory', '')}",
                f"Recommended action: {recommendation.get('action', '')}",
                f"Rationale: {recommendation.get('why', '')}",
                f"Alternatives: {alternatives}",
                f"Evaluation criteria: {criteria}",
                f"Observed evidence: {evidence}",
                f"Uncertainty: {uncertainty}",
                f"Risk: {risk.get('level', 'moderate')}",
                f"Decision questions: {reasoning.get('decision', {})}",
                f"Next action: {reasoning.get('next_action', '')}",
                "Keep implementation mechanics out of the founder-facing response.",
            ]
        )
