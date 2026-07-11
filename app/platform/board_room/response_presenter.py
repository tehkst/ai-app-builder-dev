from __future__ import annotations

from typing import Any


class ResponsePresenter:
    """Presents reasoning in concise founder-facing language."""

    def present(self, reasoning: dict[str, Any]) -> str:
        if reasoning.get("intent") == "casual":
            return "Good to hear from you. What would you like to work through?"
        if reasoning.get("intent") == "clarify":
            return "What business outcome would you like us to achieve?"

        recommendation = reasoning.get("recommendation") or {}
        risk = reasoning.get("risk") or {}
        alternatives = reasoning.get("alternatives") or []
        alternative_lines = [
            f"- {item.get('option')}: {item.get('trade_off')}"
            for item in alternatives
        ]
        lines = [
            f"Recommendation: {recommendation.get('action', 'Review the request')}",
            "",
            f"Why this matters: {recommendation.get('why', 'This is the clearest path to the desired outcome.')}",
            "",
            f"Context: {reasoning.get('business_context', '')}",
            f"Company memory: {reasoning.get('company_memory', '')}",
            f"Business impact: {reasoning.get('impact', '')}",
            f"Estimated effort: {reasoning.get('estimated_effort', 'To be confirmed after scope review.')}",
            f"What happens if you do not proceed: {reasoning.get('consequence_of_inaction', '')}",
            "",
            "Alternatives:",
            *alternative_lines,
            "",
            f"Risk: {str(risk.get('level') or 'moderate').title()}. {' '.join(risk.get('factors') or [])}",
            f"Recommended next step: {reasoning.get('next_action', 'Review the recommendation.')}",
        ]
        return "\n".join(line for line in lines if line is not None).strip()
