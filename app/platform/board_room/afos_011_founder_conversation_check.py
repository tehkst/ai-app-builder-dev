from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import patch

from app.platform.operating_console.service import board_room_chat


CRM_PROMPT = (
    "I want to build a CRM for small transport companies, but I am not sure who "
    "the target user should be, what the first version should include, or whether "
    "the product is commercially attractive. Think through the business, product, "
    "technical, and execution angles, then recommend what we should build first and why."
)

SCENARIOS = [
    CRM_PROMPT,
    "Build me a school management system.",
    "Why should a founder use AI Software Factory instead of Lovable, Replit, or a normal software agency?",
    (
        "We can only fund one thing next: better Jarvis intelligence, better UI, "
        "stronger code generation, or Digital Twin testing. What should we prioritize?"
    ),
    "Create and deploy a customer portal for my transport company now.",
    (
        "Review the current state of AI Software Factory. What is strongest, "
        "what is weakest, and what should we focus on next?"
    ),
    "What does MVP mean?",
]

PROHIBITED = (
    "derived_from_canonical_operational_evidence",
    "derived_from_canonical_gates",
    "project progress: {",
    "routing policy",
    "executive_reasoning",
)


def _chat(message: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    with patch(
        "app.platform.operating_console.service.require_founder",
        return_value={"authorized": True},
    ), patch(
        "app.platform.operating_console.service.invoke_ai",
        return_value={"status": "completed", "output_text": ""},
    ):
        return board_room_chat({
            "token": "validation-only",
            "message": message,
            "conversation_history": history or [],
        })


def run_checks() -> Dict[str, Any]:
    results = [_chat(prompt) for prompt in SCENARIOS]
    crm = results[0]
    crm_text = crm["board_room_response"].lower()
    assert crm["conversation_intelligence"]["mode"] == "Product Discovery"
    assert all(term in crm_text for term in ("5–50", "first version", "commercial", "trade-off", "interview"))
    assert crm["conversation_intelligence"]["decisions"][0]["state"] == "proposed"
    assert crm["conversation_intelligence"]["actions"][0]["state"] == "proposed"
    assert not crm["conversation_intelligence"]["mission_proposals"]
    assert not crm["governance"]["founder_approval_required"]

    assert results[1]["conversation_intelligence"]["mode"] == "Product Discovery"
    assert "which country's" in results[1]["board_room_response"].lower()
    assert results[2]["conversation_intelligence"]["mode"] == "Strategic Advice"
    assert "governed company operating loop" in results[2]["board_room_response"].lower()
    assert "prioritize jarvis intelligence first" in results[3]["board_room_response"].lower()

    execution = results[4]
    assert execution["conversation_intelligence"]["mode"] == "Execution Request"
    assert execution["governance"]["founder_approval_required"]
    assert "not created, implemented, or deployed anything" in execution["board_room_response"].lower()
    assert execution["conversation_intelligence"]["mission_proposals"][0]["state"] == "proposed"

    review = results[5]
    assert review["conversation_intelligence"]["mode"] == "System Review"
    assert "strongest area" in review["board_room_response"].lower()
    assert "weakest area" in review["board_room_response"].lower()

    information = results[6]
    assert information["conversation_intelligence"]["mode"] == "Information Request"
    assert information["board_room_response"].startswith("MVP means Minimum Viable Product")
    assert not information["conversation_intelligence"]["decisions"]
    assert not information["conversation_intelligence"]["actions"]

    follow_up = _chat(
        "What should we build first for them?",
        [
            {"role": "founder", "text": "Focus on transport companies with fewer than 50 vehicles."},
            {"role": "jarvis", "text": "Understood. I will keep that segment as the decision context."},
        ],
    )
    assert follow_up["conversation_intelligence"]["mode"] == "Conversational Follow Up"
    assert "enquiry-to-payment" in follow_up["board_room_response"].lower()

    with patch(
        "app.platform.operating_console.service.require_founder",
        return_value={"authorized": True},
    ), patch(
        "app.platform.operating_console.service.invoke_ai",
        side_effect=RuntimeError("provider unavailable"),
    ):
        provider_failure = board_room_chat({
            "token": "validation-only",
            "message": "What does MVP mean?",
        })
    assert "provider is temporarily unavailable" in provider_failure["board_room_response"].lower()
    assert "not taken any action" in provider_failure["board_room_response"].lower()

    serialized = json.dumps(results + [follow_up, provider_failure], sort_keys=True).lower()
    assert all(term not in serialized for term in PROHIBITED)
    assert "validation-only" not in serialized
    return {
        "status": "passed",
        "scenario_count": len(results) + 1,
        "modes": [item["conversation_intelligence"]["mode"] for item in results]
        + [follow_up["conversation_intelligence"]["mode"]],
    }


def main() -> None:
    print(json.dumps(run_checks(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
