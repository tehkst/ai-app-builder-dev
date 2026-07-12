from __future__ import annotations

from typing import Any

from app.platform.board_room.executive_decision_engine import ExecutiveDecisionEngine


class RecommendationGenerator:
    """Adapts the executive decision model to the Board Room response contract."""

    def generate(
        self,
        founder_request: str,
        context: dict[str, Any],
        *,
        response_mode: str,
        decomposition: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        decision_result = ExecutiveDecisionEngine().evaluate(
            founder_request,
            context,
            response_mode=response_mode,
            decomposition=decomposition,
        )
        intent = str(decision_result["objective"])
        risk = decision_result["risk"]
        recommendation = decision_result["recommendation"]
        alternatives = [
            {
                "option": option["option"],
                "trade_off": option["trade_off"],
                "score": option["score"],
                "criteria": option.get("criteria") or {},
            }
            for option in decision_result["options"]
        ]
        effort = str(decision_result["estimated_effort"])
        consequence = str(decision_result["consequence_of_inaction"])
        source_status = context.get("source_status") or {}
        available_sources = sum(value != "unavailable" for value in source_status.values())

        next_action = str(decision_result["next_action"])
        decision = {
            "why_should_i_do_this": recommendation["why"],
            "what_happens_if_i_do_not": consequence,
            "what_is_the_risk": f"{risk['level'].title()}. {' '.join(risk['factors'])}",
            "what_is_my_decision": next_action,
        }
        return {
            "intent": intent,
            "decision_requested": decision_result["decision_requested"],
            "request_decomposition": decision_result["request_decomposition"],
            "presentation_mode": decision_result["presentation_mode"],
            "business_context": self._business_context(intent, decision_result),
            "company_memory": self._memory_summary(context),
            "impact": decision_result["business_impact"],
            "estimated_effort": effort,
            "recommendation": recommendation,
            "alternatives": alternatives,
            "risk": risk,
            "constraints": decision_result["constraints"],
            "evaluation_criteria": decision_result["evaluation_criteria"],
            "evidence": decision_result["evidence"],
            "uncertainty": decision_result["uncertainty"],
            "consequence_of_inaction": consequence,
            "next_action": next_action,
            "decision": decision,
            "governance": self._governance(intent, response_mode),
            "confidence": "high" if available_sources >= 3 else "medium",
            "technical_details": {
                "intent_type": intent,
                "context_sources": source_status,
                "context_observations": context.get("observations") or {},
                "decision_frame": {
                    "objective": decision_result["objective"],
                    "decision_requested": decision_result["decision_requested"],
                    "presentation_mode": decision_result["presentation_mode"],
                    "constraints": decision_result["constraints"],
                    "evaluation_criteria": decision_result["evaluation_criteria"],
                    "evidence": decision_result["evidence"],
                    "uncertainty": decision_result["uncertainty"],
                },
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
    def _business_context(intent: str, decision_result: dict[str, Any]) -> str:
        decision_requested = str(decision_result["decision_requested"])
        criteria = ", ".join(
            str(item["name"])
            for item in decision_result["evaluation_criteria"][:3]
        )
        return f"The founder wants to {intent.lower()}. The decision is to {decision_requested}, evaluated primarily on {criteria}."

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
    def _governance(intent: str, response_mode: str) -> dict[str, Any]:
        requires_approval = response_mode not in {"casual", "clarify"}
        return {
            "required": requires_approval,
            "who": "Founder" if requires_approval else "No approval needed",
            "what": "Scope and consequential action" if requires_approval else "Conversation only",
            "why": "Existing governance remains authoritative.",
            "next": "Use the relevant existing approval flow when action is ready.",
        }
