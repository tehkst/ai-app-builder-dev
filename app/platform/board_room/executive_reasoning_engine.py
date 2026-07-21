from __future__ import annotations

from typing import Any

from app.platform.board_room.context_retriever import ContextRetriever
from app.platform.board_room.recommendation_generator import RecommendationGenerator
from app.platform.board_room.request_decomposer import RequestDecomposer
from app.platform.board_room.response_presenter import ResponsePresenter


class ExecutiveReasoningEngine:
    """Runs the read-only executive reasoning pipeline before Board Room action."""

    def __init__(self) -> None:
        self.context_retriever = ContextRetriever()
        self.recommendation_generator = RecommendationGenerator()
        self.response_presenter = ResponsePresenter()

    def reason(
        self,
        founder_request: str,
        *,
        response_mode: str,
        decomposition: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # Clarification requests must still hydrate executive context. Previously,
        # clarify mode used the same lightweight path as casual conversation,
        # which allowed Jarvis to fall back to a generic assistant response even
        # while durable mission or executive context was available.
        lightweight = response_mode == "casual"
        decomposition = decomposition or RequestDecomposer().decompose(founder_request)
        context = self.context_retriever.retrieve(
            founder_request,
            lightweight=lightweight,
            decomposition=decomposition,
        )
        reasoning = self.recommendation_generator.generate(
            founder_request,
            context,
            response_mode=response_mode,
            decomposition=decomposition,
        )
        self._enforce_context_continuity(reasoning, context, response_mode=response_mode)
        return {
            "reasoning": reasoning,
            "founder_response": self.response_presenter.present(reasoning),
            "context": context,
            "technical_details": reasoning.get("technical_details") or {},
        }

    @staticmethod
    def _enforce_context_continuity(
        reasoning: dict[str, Any],
        context: dict[str, Any],
        *,
        response_mode: str,
    ) -> None:
        """Prevent a silent return to generic clarification when context exists.

        This reuses the existing ContextRetriever, Executive Intelligence,
        Mission Pipeline and response presenter. It does not introduce a second
        memory store or another mission registry.
        """

        continuity = context.get("executive_continuity") or {}
        if response_mode != "clarify" or not continuity.get("has_context"):
            return

        decomposition = dict(reasoning.get("request_decomposition") or {})
        decomposition["dominant_goal"] = "analyze_existing"
        decomposition["lifecycle_context"] = str(
            continuity.get("lifecycle_context") or "mission_continuation"
        )
        reasoning["request_decomposition"] = decomposition
        reasoning["presentation_mode"] = "diagnosis"

        mission_id = str(continuity.get("mission_id") or "").strip()
        blocker = str(continuity.get("blocking_reason") or "").strip()
        source_failures = continuity.get("source_failures") or []

        subject = f"mission {mission_id}" if mission_id else "the current executive context"
        if blocker:
            action = f"Continue diagnosing {subject} from its preserved blocker: {blocker}"
            why = "The request is a continuation of known executive work, so asking the founder to restate the business outcome would discard available context."
        else:
            action = f"Continue from {subject} and resolve the first missing evidence link"
            why = "Existing executive context is available and must be used before asking a generic clarification question."

        reasoning["recommendation"] = {
            "action": action,
            "why": why,
            "confidence": "high" if mission_id else "medium",
        }
        reasoning["next_action"] = (
            "Inspect the preserved mission/runtime evidence and identify the exact broken read path."
            if mission_id
            else "Use the available Executive Intelligence and mission history to continue the current investigation."
        )

        evidence = list(reasoning.get("evidence") or [])
        continuity_evidence = []
        if mission_id:
            continuity_evidence.append(
                {"fact": f"Executive context references mission {mission_id}.", "source": "executive_continuity"}
            )
        if blocker:
            continuity_evidence.append(
                {"fact": f"The preserved blocking reason is {blocker}.", "source": "executive_continuity"}
            )
        if source_failures:
            continuity_evidence.append(
                {
                    "fact": "Context sources requiring attention: " + ", ".join(str(item) for item in source_failures),
                    "source": "executive_continuity",
                }
            )
        reasoning["evidence"] = continuity_evidence + evidence
        reasoning.setdefault("technical_details", {})["executive_context_continuity"] = continuity

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
