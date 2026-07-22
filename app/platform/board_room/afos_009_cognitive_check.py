from __future__ import annotations

import json
from unittest.mock import patch

from app.platform.board_room.conversation_mode import ConversationModeClassifier
from app.platform.board_room.executive_response_critic import ExecutiveResponseCritic
from app.platform.board_room.request_decomposer import RequestDecomposer
from app.platform.operating_console.service import _classify_board_room_intent, board_room_chat


AGENTS_PROMPT = "why only 3 roles in agents? and the 3 tabs are not clickable to see their skills or edit their skills"


def _authorized(_: dict) -> dict:
    return {"authorized": True, "email": "founder@example.com"}


def _generic_ai(_: dict) -> dict:
    return {"status": "completed", "output_text": "generic response"}


def _chat(prompt: str) -> dict:
    with patch("app.platform.operating_console.service.require_founder", _authorized), patch(
        "app.platform.operating_console.service.invoke_ai", _generic_ai
    ):
        return board_room_chat({"token": "founder", "message": prompt, "provider": "deepseek", "model": "deepseek-v4-pro"})


def main() -> None:
    agents = _chat(AGENTS_PROMPT)
    assert agents["action_metadata"]["intent_type"] in {"direct_answer", "product_review", "technical_diagnosis"}
    assert agents["action_metadata"]["action_buttons"] == []
    answer = agents["board_room_response"]
    assert "three summary groups" in answer and "Verified" in answer and "inference" in answer
    assert not any(label in answer for label in ("Recommendation:", "Why:", "Context:", "Risk:", "Next Step:"))

    strategic = _chat("Do you think we should expose all registered agents to the founder?")
    assert strategic["action_metadata"]["intent_type"] == "strategic_advice"
    assert strategic["action_metadata"]["action_buttons"] == []
    assert "My view" in strategic["board_room_response"]

    brainstorming = _chat("Brainstorm how Jarvis could feel more like a brilliant co-founder.")
    assert brainstorming["action_metadata"]["intent_type"] == "brainstorming"
    assert brainstorming["action_metadata"]["action_buttons"] == []

    explanation = _chat("Explain how Mission Execution works.")
    assert explanation["action_metadata"]["intent_type"] == "explanation"
    assert "durable workflow run" in explanation["board_room_response"]
    assert explanation["action_metadata"]["action_buttons"] == []

    implementation = _chat("Fix the Agents page so I can inspect every registered agent and edit permitted skills.")
    labels = [button["label"] for button in implementation["action_metadata"]["action_buttons"]]
    assert implementation["action_metadata"]["intent_type"] == "implementation_handoff"
    assert {"Approve Mission", "Edit Scope", "Reject"}.issubset(labels)
    assert implementation["action_metadata"]["effort_band"]
    assert implementation["action_metadata"]["estimated_effort"]
    assert implementation["governance"]["execution_allowed"] is False

    approval_without_context = _chat("approve")
    assert "do not have a pending" in approval_without_context["board_room_response"]
    assert approval_without_context["action_metadata"]["action_buttons"] == []

    disagreement = _chat("I think every user message should automatically become a mission.")
    assert "I disagree" in disagreement["board_room_response"]
    assert "Conversation should clarify intent first" in disagreement["board_room_response"]

    capability = _chat("Jarvis, what can you do completely on your own?")
    limitation = _chat("What can you NOT do?")
    assert capability["action_metadata"]["action_buttons"] == []
    assert limitation["action_metadata"]["action_buttons"] == []
    assert "I cannot act outside" in limitation["board_room_response"]

    stale = _chat("What do you think of the Agents page?")
    assert "MISSION-" not in stale["board_room_response"] and "preserved blocker" not in stale["board_room_response"]

    responses = [agents, strategic, brainstorming, explanation, implementation, approval_without_context, disagreement, capability, limitation, stale]
    serialized = json.dumps(responses)
    for forbidden in ("executive_reasoning", "technical_details", "context_snapshot", "critic output", "/100"):
        assert forbidden not in serialized

    modes = {
        _classify_board_room_intent(prompt)["response_mode"]
        for prompt in (AGENTS_PROMPT, "Brainstorm ways to improve onboarding.", "Explain how Mission Execution works.", "Fix the Agents page.")
    }
    assert len(modes) == 4

    quality = ExecutiveResponseCritic.evaluate(
        "Recommendation:\nDo a mission.\nWhy:\nBecause.\nContext:\nUnknown.\nRisk:\nLow.",
        mode="direct_answer",
        founder_message="Why?",
    )
    assert quality.acceptable is False and "forced_executive_template" in quality.signals

    decomposition = RequestDecomposer().decompose(AGENTS_PROMPT)
    assert ConversationModeClassifier.classify(AGENTS_PROMPT, decomposition).action_allowed is False
    print("AFOS-009 Jarvis cognitive intelligence checks passed")


if __name__ == "__main__":
    main()
