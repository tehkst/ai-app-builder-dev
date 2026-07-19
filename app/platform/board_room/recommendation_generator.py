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
        decomposition = decision_result["request_decomposition"]
        dominant_goal = str(decomposition.get("dominant_goal") or "")
        if dominant_goal == "create_new_mission":
            recommendation = {
                "action": "Create one focused mission and prepare it to the founder approval boundary",
                "why": "The requested outcome is clear enough to scope and plan without starting repository execution.",
                "confidence": recommendation.get("confidence", "high"),
            }
            next_action = "Review and approve the focused mission scope, then continue to planning. Repository execution remains stopped."
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
            "journey_evidence": context.get("journey_evidence") or {},
            "evidence_relevance": context.get("evidence_relevance") or {},
            "uncertainty": decision_result["uncertainty"],
            "capability_findings": self._capability_findings(context),
            "operational_findings": self._operational_findings(context),
            "consequence_of_inaction": consequence,
            "next_action": next_action,
            "decision": decision,
            "governance": self._governance(intent, response_mode),
            "confidence": "high" if available_sources >= 3 else "medium",
            "technical_details": {
                "intent_type": intent,
                "context_sources": source_status,
                "context_observations": context.get("observations") or {},
                "evidence_relevance": context.get("evidence_relevance") or {},
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
    def _capability_findings(context: dict[str, Any]) -> list[dict[str, Any]]:
        source = (context.get("sources") or {}).get("capability_intelligence") or {}
        ignored = {"founder", "question", "review", "what", "next", "build"}
        findings = []
        for item in source.get("capabilities") or []:
            matched = [str(term) for term in item.get("matched_terms") or [] if str(term) not in ignored]
            if not matched:
                continue
            findings.append({
                "capability": item.get("canonical_name"),
                "capability_id": item.get("capability_id"),
                "lifecycle": item.get("lifecycle_classification"),
                "integration": item.get("integration_status"),
                "production": item.get("production_status"),
                "matched_terms": matched,
                "source_paths": list(item.get("source_paths") or [])[:4],
                "confidence": item.get("confidence"),
            })
        return findings[:8]

    @staticmethod
    def _operational_findings(context: dict[str, Any]) -> list[dict[str, str]]:
        sources = context.get("sources") or {}
        findings = []
        for name in ("repository_intelligence", "deployment", "production_verification", "health", "validation"):
            source = sources.get(name)
            if not isinstance(source, dict):
                continue
            detail = source.get("status") or source.get("overall_result") or "available"
            if name == "repository_intelligence":
                detail = "%s; %s bounded files inspected" % (detail, len(source.get("manifest") or []))
            elif name == "deployment":
                detail = "%s; target %s in %s" % (detail, source.get("service_name") or "unknown", source.get("region") or "unknown")
            elif name == "production_verification":
                detail = "%s; verification service %s" % (detail, source.get("service_name") or "unknown")
            findings.append({"source": name.replace("_", " ").title(), "detail": str(detail)})
        return findings

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
        requires_approval = response_mode in {"implementation_handoff", "mission_preparation", "governed_action"}
        return {
            "required": requires_approval,
            "who": "Founder" if requires_approval else "No approval needed",
            "what": "Scope and consequential action" if requires_approval else "Conversation only",
            "why": "Existing governance remains authoritative.",
            "next": "Use the relevant existing approval flow when action is ready.",
        }
