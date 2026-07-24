from __future__ import annotations

from typing import Any, Dict, List


class AssumptionEngine:
    """Derive a small set of decision-critical assumptions without taking action."""

    def infer(self, message: str, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        context = " ".join(
            [str(item.get("text") or "") for item in history if isinstance(item, dict)]
            + [message]
        ).lower()
        assumptions: List[Dict[str, Any]] = []
        if "transport" in context:
            assumptions.append(self._item(
                "target_customer",
                "The first customer is an owner-led transport operator with 5-50 vehicles.",
                "medium",
                "high",
                [
                    "Owner-led operator with 5-50 vehicles",
                    "Operations-led fleet with more than 50 vehicles",
                ],
            ))
        elif "school" in context:
            assumptions.append(self._item(
                "primary_user",
                "The first user is the administrator of a small private school.",
                "low",
                "high",
                ["School administrator", "School owner", "Teacher"],
            ))
        elif "crm" in context:
            assumptions.append(self._item(
                "target_customer",
                "The first customer is a small service business with a repeated enquiry-to-payment workflow.",
                "low",
                "high",
                ["Small service business", "Mid-market operations team"],
            ))
        if any(term in context for term in ("build", "implement", "create", "product", "mvp")):
            assumptions.append(self._item(
                "scope",
                "The first release should prove one complete customer outcome before adding adjacent features.",
                "medium",
                "medium",
                ["One end-to-end workflow", "A broader multi-workflow release"],
            ))
        return assumptions[:3]

    @staticmethod
    def _item(
        key: str,
        statement: str,
        confidence: str,
        impact: str,
        options: List[str],
    ) -> Dict[str, Any]:
        return {
            "id": key,
            "statement": statement,
            "state": "proposed",
            "confidence": confidence,
            "decision_impact": impact,
            "options": options,
            "source": "inferred_from_founder_conversation",
        }
