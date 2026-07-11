from __future__ import annotations

import re
from typing import Any


class RecommendationGenerator:
    """Produces a business recommendation from founder intent and existing context."""

    def generate(
        self,
        founder_request: str,
        context: dict[str, Any],
        *,
        response_mode: str,
    ) -> dict[str, Any]:
        request = " ".join(founder_request.split())
        normalized = request.lower()
        intent = self._intent(request, response_mode)
        risk = self._risk(normalized)
        recommendation = self._recommendation(intent, risk)
        alternatives = self._alternatives(intent)
        effort = self._effort(normalized, risk)
        consequence = self._consequence(intent)
        source_status = context.get("source_status") or {}
        available_sources = sum(value != "unavailable" for value in source_status.values())

        next_action = self._next_action(intent, response_mode)
        decision = {
            "why_should_i_do_this": recommendation["why"],
            "what_happens_if_i_do_not": consequence,
            "what_is_the_risk": f"{risk['level'].title()}. {' '.join(risk['factors'])}",
            "what_is_my_decision": next_action,
        }
        return {
            "intent": intent,
            "business_context": self._business_context(intent),
            "company_memory": self._memory_summary(context),
            "impact": self._impact(intent, risk),
            "estimated_effort": effort,
            "recommendation": recommendation,
            "alternatives": alternatives,
            "risk": risk,
            "consequence_of_inaction": consequence,
            "next_action": next_action,
            "decision": decision,
            "governance": self._governance(intent, response_mode),
            "confidence": "high" if available_sources >= 3 else "medium",
            "technical_details": {
                "intent_type": intent,
                "context_sources": source_status,
                "context_observations": context.get("observations") or {},
                "reasoning_stages": [
                    "intent",
                    "business context",
                    "company memory",
                    "mission history",
                    "architecture knowledge",
                    "repository intelligence",
                    "risk analysis",
                    "alternatives",
                    "recommendation",
                    "handoff readiness",
                ],
            },
        }

    @staticmethod
    def _intent(request: str, response_mode: str) -> str:
        if response_mode in {"casual", "clarify"}:
            return response_mode
        milestone = re.search(r"\b[A-Z]{2,}(?:-[A-Z0-9]+)+-\d+\b", request.upper())
        if milestone:
            return f"deliver {milestone.group(0)}"
        lowered = request.lower()
        if any(term in lowered for term in ("deploy", "release", "production")):
            return "prepare a production change"
        if any(term in lowered for term in ("architecture", "strategy", "roadmap", "recommend")):
            return "make a strategic decision"
        if any(term in lowered for term in ("implement", "build", "fix", "create")):
            return "deliver a product improvement"
        return "evaluate the founder request"

    @staticmethod
    def _risk(request: str) -> dict[str, Any]:
        elevated = any(term in request for term in ("production", "deploy", "merge", "rollback", "auth", "secret"))
        low_risk = any(term in request for term in ("ui polish", "visual polish", "copy change", "styling")) and not elevated
        return {
            "level": "high" if elevated else ("low" if low_risk else "moderate"),
            "factors": [
                "The change may affect a governed production or repository action."
                if elevated
                else (
                    "The request is limited to presentation and should not affect platform behavior."
                    if low_risk
                    else "The full impact depends on the final scope and affected capabilities."
                )
            ],
            "mitigations": ["Confirm scope and success measures before execution.", "Keep existing approval gates in place."],
            "impact_if_fail": "Delivery may be delayed; existing operations remain the fallback.",
        }

    @staticmethod
    def _recommendation(intent: str, risk: dict[str, Any]) -> dict[str, str]:
        if intent in {"casual", "clarify"}:
            return {"action": "Continue the conversation", "why": "No governed action is needed.", "confidence": "high"}
        if risk["level"] == "high":
            return {"action": "Define the decision and review its safeguards before proceeding", "why": "The request touches a governed capability where failure could affect production or source control.", "confidence": "high"}
        if risk["level"] == "low":
            return {"action": "Proceed with a focused, low-risk improvement", "why": "It improves the founder experience without changing platform behavior or weakening governance.", "confidence": "high"}
        return {"action": "Proceed with a focused mission proposal", "why": "The request is actionable and can be scoped without changing existing governance.", "confidence": "medium"}

    @staticmethod
    def _alternatives(intent: str) -> list[dict[str, str]]:
        if intent in {"casual", "clarify"}:
            return []
        return [
            {"option": "Focused mission", "trade_off": "Fastest path with a controlled scope and clear success measures."},
            {"option": "Broader review", "trade_off": "More confidence and context, but a slower decision."},
            {"option": "Defer", "trade_off": "Avoids near-term risk but delays the expected business value."},
        ]

    @staticmethod
    def _business_context(intent: str) -> str:
        return f"This request would help AI Software Factory {intent} while preserving founder control over consequential actions."

    @staticmethod
    def _impact(intent: str, risk: dict[str, Any]) -> str:
        return f"The likely benefit is clearer and faster delivery. Current risk is {risk['level']} until scope is confirmed."

    @staticmethod
    def _effort(request: str, risk: dict[str, Any]) -> str:
        if risk["level"] == "low" and any(term in request for term in ("small", "polish", "copy", "styling")):
            return "Approximately 30-60 minutes for planning and implementation."
        if risk["level"] == "high":
            return "A detailed review is required before a reliable estimate can be given."
        return "Approximately 1-3 hours once the scope is confirmed."

    @staticmethod
    def _consequence(intent: str) -> str:
        if intent in {"casual", "clarify"}:
            return "Nothing changes; the conversation can continue when useful."
        return "Current operations remain functional, but the expected improvement and its business value are delayed."

    @staticmethod
    def _memory_summary(context: dict[str, Any]) -> str:
        sources = context.get("sources") or {}
        available = [name.replace("_", " ") for name, value in sources.items() if value.get("status") != "unavailable"]
        if not available:
            return "No reliable company history was available for this response."
        observations = context.get("observations") or {}
        active = observations.get("active_missions", 0)
        blocked = observations.get("blocked_missions", 0)
        return (
            "The recommendation considers current "
            + ", ".join(available)
            + f". Mission history currently reports {active} active and {blocked} blocked mission(s)."
        )

    @staticmethod
    def _next_action(intent: str, response_mode: str) -> str:
        if response_mode == "casual":
            return "Continue the conversation."
        if response_mode == "clarify":
            return "Clarify the desired business outcome."
        if response_mode == "implementation_handoff":
            return "Review the proposed plan and authorize engineering when ready."
        return "Review the recommendation and decide whether to create a mission."

    @staticmethod
    def _governance(intent: str, response_mode: str) -> dict[str, Any]:
        requires_approval = response_mode not in {"casual", "clarify"}
        return {
            "required": requires_approval,
            "who": "Founder" if requires_approval else "No approval needed",
            "what": "Scope and consequential action" if requires_approval else "Conversation only",
            "why": "Existing governance remains authoritative.",
            "next": "Use the relevant existing approval flow when action is ready.",
        }
