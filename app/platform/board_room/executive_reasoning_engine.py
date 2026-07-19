from __future__ import annotations

from typing import Any

from app.platform.board_room.context_retriever import ContextRetriever
from app.platform.board_room.capability_router import CapabilityRouter
from app.platform.board_room.recommendation_generator import RecommendationGenerator
from app.platform.board_room.request_decomposer import RequestDecomposer
from app.platform.board_room.response_presenter import ResponsePresenter


class ExecutiveReasoningEngine:
    """Runs the read-only executive reasoning pipeline before Board Room action."""

    def __init__(self) -> None:
        self.context_retriever = ContextRetriever()
        self.capability_router = CapabilityRouter()
        self.recommendation_generator = RecommendationGenerator()
        self.response_presenter = ResponsePresenter()

    def reason(
        self,
        founder_request: str,
        *,
        response_mode: str,
        decomposition: dict[str, Any] | None = None,
        capability_route: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        lightweight = response_mode in {"casual", "clarify"}
        decomposition = decomposition or RequestDecomposer().decompose(founder_request)
        capability_route = capability_route or self.capability_router.route(founder_request, decomposition)
        context = self.context_retriever.retrieve(
            founder_request,
            lightweight=lightweight,
            decomposition=decomposition,
            capability_route=capability_route,
        )
        reasoning = self.recommendation_generator.generate(
            founder_request,
            context,
            response_mode=response_mode,
            decomposition=decomposition,
        )
        return {
            "reasoning": reasoning,
            "founder_response": self.response_presenter.present(reasoning),
            "context": context,
            "technical_details": reasoning.get("technical_details") or {},
            "capability_route": capability_route,
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
        decomposition = reasoning.get("request_decomposition") or {}
        return "\n".join(
            [
                "Lead with the recommendation and use concise business language.",
                f"Presentation mode hint: {presentation_mode}",
                f"Dominant founder goal: {decomposition.get('dominant_goal', 'decision support')}",
                f"Lifecycle context: {decomposition.get('lifecycle_context', 'unknown')}",
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
                "Write a natural executive response. Do not force headings or repeat sections that add no value.",
                "Keep implementation mechanics out of the founder-facing response.",
            ]
        )
