from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from app.platform.board_room.cognitive_core import JarvisCognitiveCore
from app.platform.board_room.conversation_mode import ACTION_MODES, CONVERSATIONAL_MODES, ConversationModeClassifier
from app.platform.board_room.executive_response_critic import ExecutiveResponseCritic
from app.platform.board_room.founder_conversation_contract import FounderConversationContract
from app.platform.board_room.founder_response_composer import FounderResponseComposer
from app.platform.board_room.request_decomposer import RequestDecomposer
from app.platform.operating_console.service import board_room_chat


COMPARISON_PROMPT = (
    "Jarvis how do you grade your intelligence level? Maybe you can reference OpenAI, Claude AI, "
    "Gemini AI, Lovable, Replit as well as Codex. Provide your answer in a table format so it is "
    "easier to view the comparison."
)
ARCHITECTURE_PROMPT = "Hi Jarvis, are you able to explain your whole setup and architecture in detail to me?"
INFORMATIONAL_FAMILIES = {
    "INFORMATION_REQUEST", "ARCHITECTURE_EXPLANATION", "ARCHITECTURE_REVIEW",
    "CAPABILITY_DESCRIPTION", "CAPABILITY_COMPARISON", "STATUS_REQUEST",
}


def _decompose_and_classify(
    prompt: str,
    history: list[dict[str, Any]] | None = None,
) -> tuple[str, Any, dict[str, Any]]:
    decomposition = RequestDecomposer().decompose(prompt)
    mode = ConversationModeClassifier.classify(
        prompt,
        decomposition,
        conversation_history=history,
    ).mode
    contract = FounderConversationContract.classify(
        prompt,
        response_mode=mode,
        decomposition=decomposition,
        conversation_history=history,
    )
    return mode, contract, decomposition


def _comparison_answer() -> str:
    return """There is no defensible single intelligence score because these systems serve different jobs.

| System | Primary strength | Best suited for | Limitation / uncertainty |
|---|---|---|---|
| Jarvis | Governed executive orchestration | Founder-led delivery | No independent intelligence benchmark |
| OpenAI | General model ecosystem | Broad reasoning | Performance varies by model |
| Claude AI | Long-context synthesis | Document analysis | Current performance is not measured here |
| Gemini AI | Multimodal and Google integration | Google workflows | Current performance is not measured here |
| Lovable | Rapid app generation | Product prototypes | Different operating focus |
| Replit | Cloud coding workspace | Interactive development | Different operating focus |
| Codex | Repository engineering | Coding and review | Authority depends on its environment |

Jarvis is specialized rather than universally superior. Current comparative quality cannot be verified from repository evidence alone."""


def _context() -> dict[str, Any]:
    return {
        "sources": {
            "executive_intelligence": {
                "status": "executive-state-ready",
                "state_contract_version": "executive-state-v1",
            },
            "repository_intelligence": {
                "status": "repository-intelligence-ready",
                "repository_areas": {"runtime": [], "mission_execution": []},
            },
        },
        "source_status": {
            "executive_intelligence": "executive-state-ready",
            "repository_intelligence": "repository-intelligence-ready",
        },
        "observations": {"active_missions": 0, "blocked_missions": 0},
    }


def _board_chat(
    prompt: str,
    history: list[dict[str, str]],
    *,
    prior_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with patch(
        "app.platform.operating_console.service.require_founder",
        return_value={"authorized": True},
    ), patch(
        "app.platform.operating_console.service.ContextRetriever.retrieve",
        return_value=_context(),
    ), patch(
        "app.platform.operating_console.service.invoke_ai",
        return_value={"status": "failed", "output_text": ""},
    ), patch(
        "app.platform.operating_console.service.load_decision_experience",
        return_value=prior_decision,
    ):
        return board_room_chat({
            "token": "validation-only",
            "message": prompt,
            "conversation_id": "CONVERSATION-ISOLATION",
            "conversation_history": history,
        })


def main() -> None:
    registered = CONVERSATIONAL_MODES | ACTION_MODES
    assert FounderConversationContract.registered_modes_are_explicit()
    assert registered <= set(FounderConversationContract.MODE_TO_CONTRACT)
    assert set(FounderConversationContract.MODE_TO_CONTRACT.values()) <= FounderResponseComposer.FALLBACK_FAMILIES

    for response_mode, family in FounderConversationContract.MODE_TO_CONTRACT.items():
        contract = FounderConversationContract._contract(family)
        if family in INFORMATIONAL_FAMILIES:
            assert family != "STRATEGIC_ADVICE", response_mode
            assert not {"DECISION", "ACTION", "MISSION_PROPOSAL"} & set(contract.permissible_artifacts)
        fallback = FounderResponseComposer._fallback("Explain the current state.", contract, _context(), [])
        assert fallback.strip(), (response_mode, family)

    taxonomy = {
        "Explain the platform architecture.": "architecture_explanation",
        "Review the platform architecture for coherence.": "architecture_review",
        "Which architecture improvement should we prioritize next?": "architecture_recommendation",
        "What can Jarvis do?": "capability_query",
        COMPARISON_PROMPT: "capability_comparison",
        "Compare OpenAI, Claude AI, and Gemini AI in a table.": "competitive_comparison",
        "Which should we prioritize: Jarvis or code generation?": "strategic_advice",
        "Build a CRM for a transport company.": "product_discovery",
        "What is the current status of the CRM mission?": "status_request",
        "Deploy the approved release now.": "execution_command",
    }
    for prompt, expected_mode in taxonomy.items():
        mode, _, _ = _decompose_and_classify(prompt)
        assert mode == expected_mode, (prompt, mode, expected_mode)

    comparison_mode, comparison_contract, decomposition = _decompose_and_classify(COMPARISON_PROMPT)
    assert comparison_mode == "capability_comparison"
    assert comparison_contract.mode == "CAPABILITY_COMPARISON"

    good_quality = ExecutiveResponseCritic.evaluate(
        _comparison_answer(),
        mode=comparison_mode,
        founder_message=COMPARISON_PROMPT,
        contract=comparison_contract,
    )
    assert good_quality.acceptable, good_quality.signals
    bad_quality = ExecutiveResponseCritic.evaluate(
        "Jarvis is the best and superior to every competitor.",
        mode=comparison_mode,
        founder_message=COMPARISON_PROMPT,
        contract=comparison_contract,
    )
    assert not bad_quality.acceptable
    assert {
        "requested_entities_missing", "requested_table_missing",
        "comparison_dimensions_missing", "uncertainty_missing",
        "unsupported_superiority_claim",
    } <= set(bad_quality.signals)

    for provider, model in (("deepseek", "deepseek-v4-pro"), ("openai", "gpt-5.5")):
        calls: list[dict[str, Any]] = []

        def invoke(payload: dict[str, Any]) -> dict[str, Any]:
            calls.append(payload)
            return {"status": "completed", "output_text": _comparison_answer()}

        outcome = JarvisCognitiveCore.respond_with_outcome(
            founder_message=COMPARISON_PROMPT,
            mode=comparison_mode,
            context=_context(),
            invoke=invoke,
            decomposition=decomposition,
            provider=provider,
            model=model,
            contract=comparison_contract,
        )
        assert calls[0]["provider"] == provider and calls[0]["model"] == model
        assert "| System |" in outcome["text"]
        assert not outcome["decisions"] and not outcome["actions"] and not outcome["mission_proposals"]

    histories = [
        [],
        [{"role": "jarvis", "text": "My recommendation is to prioritize customer evidence."}],
        [{"role": "jarvis", "text": "The target customer assumption is a transport operator."}],
        [{"role": "jarvis", "text": "Mission MISSION-123 is awaiting approval."}],
    ]
    stale_decision = {
        "decision_id": "DECISION-OLD",
        "assumptions": [{"id": "A-OLD", "state": "confirmed", "statement": "Old assumption"}],
    }
    for history in histories:
        for prompt, expected_family in (
            (ARCHITECTURE_PROMPT, "ARCHITECTURE_EXPLANATION"),
            (COMPARISON_PROMPT, "CAPABILITY_COMPARISON"),
        ):
            result = _board_chat(prompt, history, prior_decision=stale_decision)
            intelligence = result["conversation_intelligence"]
            assert intelligence["mode"] == expected_family.replace("_", " ").title()
            assert intelligence["decision_experience"] is None
            assert not intelligence["decisions"] and not intelligence["actions"] and not intelligence["mission_proposals"]
            assert not result["action_metadata"]["action_buttons"]
            text = result["board_room_response"].lower()
            assert "smallest step that tests the assumption" not in text
            assert "strongest customer evidence" not in text
            if expected_family == "CAPABILITY_COMPARISON":
                assert "| system |" in text

    ui_source = (
        Path(__file__).parents[1] / "ui" / "founder_dashboard_board_chat.py"
    ).read_text(encoding="utf-8")
    assert "renderFounderDecisionExperience(ci.decision_experience||null)" in ui_source
    assert "function markdownTables(s)" in ui_source
    assert "<table><thead><tr>" in ui_source
    print("AFOS-012.2 intent taxonomy checks passed")


if __name__ == "__main__":
    main()
