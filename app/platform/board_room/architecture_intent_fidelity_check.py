from __future__ import annotations

from pathlib import Path
from typing import Any

from app.platform.board_room.cognitive_core import JarvisCognitiveCore
from app.platform.board_room.conversation_mode import ConversationModeClassifier
from app.platform.board_room.founder_conversation_contract import FounderConversationContract
from app.platform.board_room.request_decomposer import RequestDecomposer


ARCHITECTURE_PROMPT = "Hi Jarvis, are you able to explain your whole setup and architecture in detail to me?"


def _route(message: str, history: list[dict[str, Any]] | None = None) -> tuple[str, str, dict[str, Any]]:
    decomposition = RequestDecomposer().decompose(message)
    mode = ConversationModeClassifier.classify(message, decomposition).mode
    contract = FounderConversationContract.classify(
        message,
        response_mode=mode,
        decomposition=decomposition,
        conversation_history=history,
    )
    return mode, contract.mode, decomposition


def _context(available: bool = True) -> dict[str, Any]:
    if not available:
        return {
            "sources": {
                "executive_intelligence": {"status": "unavailable"},
                "repository_intelligence": {"status": "unavailable"},
            },
            "source_status": {
                "executive_intelligence": "unavailable",
                "repository_intelligence": "unavailable",
            },
        }
    return {
        "sources": {
            "executive_intelligence": {
                "status": "executive-state-ready",
                "state_contract_version": "executive-state-v1",
                "source_evidence": {
                    "board_room": {
                        "value": {
                            "status": "consuming_executive_intelligence",
                            "canonical_contract": "executive-state-v1",
                        }
                    },
                    "capabilities": {
                        "value": {
                            "status": "capability-intelligence-ready",
                            "mode": "read-only-evidence-derived-aggregator",
                            "record_count": 42,
                        }
                    },
                },
                "governance": {"read_only": True},
            },
            "repository_intelligence": {
                "status": "repository-intelligence-ready",
                "repository_areas": {
                    "runtime": ["app/platform/runtime/service.py"],
                    "mission_execution": ["app/platform/operating_console/mission_run_service.py"],
                    "deploy": ["app/platform/deployment/approved_cloud_run.py"],
                },
            },
        },
        "source_status": {
            "executive_intelligence": "executive-state-ready",
            "repository_intelligence": "repository-intelligence-ready",
        },
    }


def _architecture_answer() -> str:
    return (
        "AI Software Factory has a founder-facing Jarvis layer, a read-only Executive Intelligence layer, "
        "and durable mission execution authorities. A founder message is classified before context is retrieved. "
        "Implementation then remains behind governance, while workflow and task records preserve durable progress. "
        "DeepSeek and OpenAI use one normalized provider boundary, and deployment requires separate approval."
    )


def main() -> None:
    expected = {
        "Explain your whole setup and architecture in detail.": ("architecture_explanation", "ARCHITECTURE_EXPLANATION"),
        "How does AI Software Factory work from my message to deployment?": ("architecture_explanation", "ARCHITECTURE_EXPLANATION"),
        "What components are already built?": ("architecture_explanation", "ARCHITECTURE_EXPLANATION"),
        "Which parts of your architecture should we improve next?": ("architecture_recommendation", "STRATEGIC_ADVICE"),
        "Should we improve Jarvis or the Native Coding Agent first?": ("strategic_advice", "STRATEGIC_ADVICE"),
        "Build a CRM for a transport company.": ("product_discovery", "PRODUCT_DISCOVERY"),
        "What is the current status of the CRM mission?": ("status_request", "STATUS_REQUEST"),
    }
    for prompt, modes in expected.items():
        mode, contract, _ = _route(prompt)
        assert (mode, contract) == modes, (prompt, mode, contract)

    for provider, model in (
        ("deepseek", "deepseek-v4-pro"),
        ("openai", "gpt-5.5"),
    ):
        calls: list[dict[str, Any]] = []

        def invoke(payload: dict[str, Any]) -> dict[str, Any]:
            calls.append(payload)
            return {"status": "completed", "output_text": _architecture_answer()}

        mode, contract_mode, decomposition = _route(ARCHITECTURE_PROMPT)
        contract = FounderConversationContract.classify(
            ARCHITECTURE_PROMPT,
            response_mode=mode,
            decomposition=decomposition,
        )
        outcome = JarvisCognitiveCore.respond_with_outcome(
            founder_message=ARCHITECTURE_PROMPT,
            mode=mode,
            context=_context(),
            invoke=invoke,
            decomposition=decomposition,
            provider=provider,
            model=model,
            contract=contract,
        )
        assert contract_mode == "ARCHITECTURE_EXPLANATION"
        assert outcome["text"] == _architecture_answer()
        assert not outcome["decisions"] and not outcome["actions"] and not outcome["mission_proposals"]
        assert calls[0]["provider"] == provider and calls[0]["model"] == model
        assert "Executive brief" not in calls[0]["prompt"]

    histories = [
        [],
        [{"role": "assistant", "text": "My recommendation is to prioritize customer evidence."}],
        [{"role": "assistant", "text": "The CRM target customer is a transport operator."}],
        [{"role": "assistant", "text": "Mission MISSION-123 is awaiting approval."}],
    ]
    for history in histories:
        mode, contract_mode, decomposition = _route(ARCHITECTURE_PROMPT, history)
        assert mode == "architecture_explanation"
        assert contract_mode == "ARCHITECTURE_EXPLANATION"

        outcome = JarvisCognitiveCore.respond_with_outcome(
            founder_message=ARCHITECTURE_PROMPT,
            mode=mode,
            context=_context(),
            invoke=lambda _payload: {"status": "failed", "output_text": ""},
            decomposition=decomposition,
            contract=FounderConversationContract.classify(
                ARCHITECTURE_PROMPT,
                response_mode=mode,
                decomposition=decomposition,
                conversation_history=history,
            ),
            conversation_history=history,
        )
        lowered = outcome["text"].lower()
        assert "strongest customer evidence" not in lowered
        assert "recommendation" not in lowered
        assert "architecture" in lowered
        assert not outcome["decisions"] and not outcome["actions"] and not outcome["mission_proposals"]

    unavailable = JarvisCognitiveCore.respond_with_outcome(
        founder_message=ARCHITECTURE_PROMPT,
        mode="architecture_explanation",
        context=_context(False),
        invoke=lambda _payload: {"status": "failed", "output_text": ""},
        decomposition=RequestDecomposer().decompose(ARCHITECTURE_PROMPT),
        contract=FounderConversationContract._contract(
            "ARCHITECTURE_EXPLANATION",
            "Explain the current platform architecture from verified evidence",
            False,
        ),
    )
    assert "could not retrieve enough verified architecture evidence" in unavailable["text"].lower()
    assert "strongest customer evidence" not in unavailable["text"].lower()

    ui_source = (
        Path(__file__).parents[1] / "ui" / "founder_dashboard_board_chat.py"
    ).read_text(encoding="utf-8")
    assert "renderFounderDecisionExperience(ci.decision_experience||null)" in ui_source
    print("Jarvis architecture intent fidelity checks passed")


if __name__ == "__main__":
    main()
