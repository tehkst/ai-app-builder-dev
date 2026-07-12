from __future__ import annotations

from app.platform.board_room.request_decomposer import RequestDecomposer
from app.platform.operating_console import service as operating_console


PRODUCTION_FAILURE_PROMPT = """I want AI Software Factory to complete one real founder software mission end-to-end through Mission Control, from my request to verified production.

Before implementing anything, inspect the current company and mission context and determine the biggest gaps preventing this journey:

Founder request → executive recommendation → founder approval → mission creation → planning → engineering execution → code changes → pull request → merge approval → merge → deployment approval → production deployment → verification → mission completion.

Do not assume we need new components. Prefer connecting and completing existing capabilities.

Tell me:
1. What already works
2. Where the journey currently breaks or requires manual work
3. The single smallest milestone that would create the biggest improvement
4. What should be reused rather than rebuilt
5. What you recommend we implement first

Do not implement anything yet. I want a decision and gap analysis first."""


def main() -> None:
    decomposer = RequestDecomposer()
    decomposition = decomposer.decompose(PRODUCTION_FAILURE_PROMPT)
    assert decomposition["requested_action"] == "DIAGNOSE"
    assert decomposition["execution_requested"] is False
    assert decomposition["governed_action_requested"] is False
    assert len(decomposition["questions_to_answer"]) == 5

    contrasts = {
        "Deploy the latest approved change to production.": ("GOVERNED_ACTION", True, True),
        "Merge the approved PR.": ("GOVERNED_ACTION", True, True),
        "Roll back the current production revision.": ("GOVERNED_ACTION", True, True),
        "Implement attachment support in Mission Control.": ("IMPLEMENT", True, False),
        "Should we build attachments or improve Board Room intelligence?": ("COMPARE", False, False),
        "Why does our founder mission journey still require manual work?": ("DIAGNOSE", False, False),
    }
    for prompt, expected in contrasts.items():
        result = decomposer.decompose(prompt)
        assert (
            result["requested_action"],
            result["execution_requested"],
            result["governed_action_requested"],
        ) == expected
        classified = operating_console._classify_board_room_intent(prompt)
        if expected[0] in {"GOVERNED_ACTION", "IMPLEMENT"}:
            assert classified["response_mode"] == "implementation_handoff"
        else:
            assert classified["response_mode"] == "structured"

    operating_console.require_founder = lambda _payload: {"authorized": True, "role": "founder"}
    operating_console.invoke_ai = lambda _payload: {"status": "completed", "output_text": "generic response"}
    response = operating_console.board_room_chat({"token": "test", "message": PRODUCTION_FAILURE_PROMPT})
    reasoning = response["executive_reasoning"]
    assert reasoning["request_decomposition"]["requested_action"] == "DIAGNOSE"
    assert reasoning["presentation_mode"] == "diagnosis"
    assert reasoning["risk"]["level"] != "high"
    assert "Requested answers:" in response["board_room_response"]
    assert all(
        question in response["board_room_response"]
        for question in decomposition["questions_to_answer"]
    )
    labels = [
        button["label"]
        for button in response["action_metadata"]["action_buttons"]
    ]
    banned_labels = {
        "Preview Deployment",
        "Open Deployment Panel",
        "Run Verification",
        "Create Execution Mission",
        "Open GitHub Execution",
    }
    assert not banned_labels.intersection(labels)
    assert labels == ["Save Analysis", "Explore Recommended Milestone"]
    assert response["action_metadata"]["intent_type"] == "diagnose"
    print("board room intent fidelity ok")


if __name__ == "__main__":
    main()
