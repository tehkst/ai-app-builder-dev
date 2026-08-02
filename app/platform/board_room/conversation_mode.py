from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional


CONVERSATIONAL_MODES = {
    "direct_answer",
    "explanation",
    "brainstorming",
    "executive_discussion",
    "strategic_advice",
    "product_discovery",
    "product_review",
    "system_review",
    "architecture_explanation",
    "architecture_review",
    "architecture_recommendation",
    "technical_diagnosis",
    "status_request",
    "capability_query",
    "limitation_query",
    "capability_comparison",
    "competitive_comparison",
    "conversational_follow_up",
}
ACTION_MODES = {"implementation_planning", "mission_recommendation", "mission_approval", "execution_command"}


@dataclass(frozen=True)
class ConversationModeDecision:
    mode: str
    consult_mission_continuity: bool = False
    action_allowed: bool = False


class ConversationModeClassifier:
    """Maps decomposed speech acts to presentation behavior, never execution authority."""

    @classmethod
    def classify(
        cls,
        message: str,
        decomposition: dict[str, Any],
        *,
        pending_approval: Optional[dict[str, Any]] = None,
        conversation_history: Optional[list[dict[str, Any]]] = None,
    ) -> ConversationModeDecision:
        normalized = " ".join(message.lower().split())
        requested = str(decomposition.get("requested_action") or "QUESTION")
        dominant = str(decomposition.get("dominant_goal") or "")

        if cls._natural_approval(normalized):
            return ConversationModeDecision(
                "mission_approval" if pending_approval else "direct_answer",
                consult_mission_continuity=bool(pending_approval),
                action_allowed=bool(pending_approval),
            )
        if decomposition.get("intent_type") == "informational_capability_query":
            limitation = bool(re.search(r"\b(?:not do|cannot|can't|limitations?)\b", normalized))
            return ConversationModeDecision("limitation_query" if limitation else "capability_query")
        if re.search(
            r"\b(?:what can jarvis do|what is jarvis capable of|describe jarvis(?:'s)? capabilities|jarvis limitations?)\b",
            normalized,
        ):
            limitation = bool(re.search(r"\b(?:not do|cannot|can't|limitations?)\b", normalized))
            return ConversationModeDecision("limitation_query" if limitation else "capability_query")
        if requested == "GOVERNED_ACTION":
            return ConversationModeDecision("execution_command", True, True)
        if cls._product_discovery(normalized, requested):
            return ConversationModeDecision("product_discovery")
        if requested == "IMPLEMENT" or dominant == "create_new_mission":
            return ConversationModeDecision("implementation_planning", False, True)
        if "ai software factory" in normalized and re.search(
            r"\b(?:review|current state|strongest|weakest|focus on)\b",
            normalized,
        ):
            return ConversationModeDecision("system_review")
        if re.search(r"\bbrainstorm|ideas? for|ways to|invent|imagine|non-obvious|three coherent\b", normalized):
            return ConversationModeDecision("brainstorming")
        if re.search(r"\b(?:let's|let us) discuss\b|\bdiscuss before (?:approval|deciding|execution)\b", normalized):
            return ConversationModeDecision("executive_discussion")
        architecture_subject = bool(re.search(
            r"\barchitecture|system design|technical design|canonical owner|canonical ownership|"
            r"read models?|reasoning services?|decision system|integration boundary|contract test|"
            r"between cognition and execution|whole setup|how .*software factory work|"
            r"components? (?:are|is) (?:already )?built\b",
            normalized,
        ))
        architecture_explanation = bool(re.search(
            r"\b(?:explain|describe|show|tell me|how does|how do|how .* works?|what components?)\b",
            normalized,
        ))
        architecture_recommendation = requested == "RECOMMEND" or bool(re.search(
            r"\b(?:should|recommend|improve next|change next|priority)\b",
            normalized,
        ))
        if architecture_subject and architecture_recommendation:
            return ConversationModeDecision("architecture_recommendation")
        if architecture_subject and architecture_explanation and requested in {"QUESTION", "ANALYZE"}:
            return ConversationModeDecision("architecture_explanation")
        if architecture_subject:
            return ConversationModeDecision("architecture_review")
        comparison_mode = cls._comparison_mode(normalized, requested)
        if comparison_mode:
            return ConversationModeDecision(comparison_mode)
        if conversation_history and cls._explicit_follow_up(normalized):
            return ConversationModeDecision("conversational_follow_up")
        if requested in {"COMPARE", "RECOMMEND"} or re.search(
            r"\b(?:why should|which should|should we).*(?:instead|choose|prioriti[sz]e|use)\b",
            normalized,
        ):
            return ConversationModeDecision("strategic_advice")
        if requested == "DIAGNOSE" or re.search(
            r"\bwhy\b|not clickable|not working|wrong with|problem|root cause|likeliest reason|"
            r"diagnos|defect|drift apart|distinguish .* defect\b",
            normalized,
        ):
            return ConversationModeDecision("technical_diagnosis")
        if re.search(r"\bstatus|where are we|progress\b", normalized):
            return ConversationModeDecision("status_request", True)
        if requested == "COMPARE" or re.search(
            r"\bshould we|we should|do you agree|i think|(?:what do|do) you think|"
            r"always\b|every(?:thing|one|\s+\w+)|enough for everything|choose between|"
            r"more valuable|gain and give up|optimi[sz]e .* or\b",
            normalized,
        ):
            return ConversationModeDecision("strategic_advice")
        if re.search(
            r"\bstrategy|strategic|positioning|differentiation|runway|where should .* company|company thesis|product thesis|"
            r"category|market|investor evidence|customer evidence|quarter of runway\b",
            normalized,
        ):
            return ConversationModeDecision("strategic_advice")
        if re.search(
            r"\bfounder experience|founder dashboard|dashboard|page|tabs?|design|onboarding|"
            r"customer|retention|churn|workflow panels?|product choice|product's emotional|trust compound\b",
            normalized,
        ):
            return ConversationModeDecision("product_review")
        if re.search(r"\bexplain|how does|how do|how .* works?\b", normalized):
            return ConversationModeDecision("explanation")
        if requested in {"ANALYZE", "RECOMMEND", "PLAN"}:
            return ConversationModeDecision("executive_discussion")
        if dominant != "continue_existing_mission" and len(normalized.split()) >= 5 and not message.rstrip().endswith("?"):
            return ConversationModeDecision("strategic_advice")
        return ConversationModeDecision("direct_answer")

    @staticmethod
    def _natural_approval(normalized: str) -> bool:
        return bool(re.fullmatch(r"(?:i\s+)?(?:approve|approved|go ahead|proceed(?: with this)?|create the mission)[.!]?", normalized))

    @staticmethod
    def _product_discovery(normalized: str, requested: str) -> bool:
        product = bool(re.search(r"\b(?:crm|management system|customer portal|app|software|mvp)\b", normalized))
        build = bool(re.search(r"\b(?:build|create|develop)\b", normalized))
        consequential = bool(re.search(r"\b(?:deploy|merge|rollback|execute|production|now)\b", normalized))
        return requested != "GOVERNED_ACTION" and product and build and not consequential

    @staticmethod
    def _comparison_mode(normalized: str, requested: str) -> str:
        entities = re.findall(
            r"\b(?:openai|claude(?: ai)?|gemini(?: ai)?|lovable|replit|codex|jarvis)\b",
            normalized,
        )
        comparison = requested == "COMPARE" or bool(re.search(
            r"\b(?:compare|comparison|versus|vs\.?|relative to|reference)\b",
            normalized,
        ))
        self_assessment = bool(re.search(
            r"\b(?:your|jarvis).{0,40}(?:intelligence|capabilit|grade|level)\b|"
            r"\b(?:grade|assess).{0,30}(?:your|jarvis)\b",
            normalized,
        ))
        choice_request = bool(re.search(
            r"\b(?:should we|why should|which should|which one|better choice|prioriti[sz]e|choose|instead of)\b",
            normalized,
        ))
        if choice_request:
            return ""
        if len(set(entities)) >= 2 and (comparison or self_assessment):
            return "capability_comparison" if self_assessment or "jarvis" in entities else "competitive_comparison"
        return ""

    @staticmethod
    def _explicit_follow_up(normalized: str) -> bool:
        return len(normalized.split()) <= 14 and bool(re.search(
            r"\b(?:it|that|this|them|those|which one|what should we .* for them|next)\b",
            normalized,
        ))
