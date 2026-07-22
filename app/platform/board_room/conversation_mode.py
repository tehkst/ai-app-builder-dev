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
    "product_review",
    "architecture_review",
    "technical_diagnosis",
    "status_request",
    "capability_query",
    "limitation_query",
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
        if requested == "GOVERNED_ACTION":
            return ConversationModeDecision("execution_command", True, True)
        if requested == "IMPLEMENT" or dominant == "create_new_mission":
            return ConversationModeDecision("implementation_planning", False, True)
        if re.search(r"\bbrainstorm|ideas? for|ways to\b", normalized):
            return ConversationModeDecision("brainstorming")
        if re.search(r"\barchitecture|system design|technical design\b", normalized):
            return ConversationModeDecision("architecture_review")
        if re.search(r"\bstatus|where are we|progress\b", normalized):
            return ConversationModeDecision("status_request", True)
        if requested == "COMPARE" or re.search(r"\bshould we|we should|do you agree|i think|(?:what do|do) you think\b", normalized):
            return ConversationModeDecision("strategic_advice")
        if requested == "DIAGNOSE" or re.search(r"\bwhy\b|not clickable|not working|wrong with|problem\b", normalized):
            return ConversationModeDecision("technical_diagnosis")
        if re.search(r"\bagents?|founder experience|page|tabs?|design|onboarding\b", normalized):
            return ConversationModeDecision("product_review")
        if re.search(r"\bexplain|how does|how do|how .* works?\b", normalized):
            return ConversationModeDecision("explanation")
        if requested in {"ANALYZE", "RECOMMEND", "PLAN"}:
            return ConversationModeDecision("executive_discussion")
        return ConversationModeDecision("direct_answer")

    @staticmethod
    def _natural_approval(normalized: str) -> bool:
        return bool(re.fullmatch(r"(?:i\s+)?(?:approve|approved|go ahead|proceed(?: with this)?|create the mission)[.!]?", normalized))
