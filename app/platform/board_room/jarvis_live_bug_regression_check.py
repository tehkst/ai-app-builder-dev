from __future__ import annotations

from unittest.mock import patch

from app.platform.architecture_knowledge_graph.board_briefing import build_architecture_graph_briefing
from app.platform.board_room.conversation_mode import ConversationModeClassifier
from app.platform.board_room.founder_conversation_contract import FounderConversationContract
from app.platform.board_room.founder_response_composer import FounderResponseComposer
from app.platform.board_room.request_decomposer import RequestDecomposer
from app.platform.persistence.database import create_platform_tables

"""Locks in two real bugs found via live founder testing on production, both
traced to their actual root cause by reading the deployed code, not guessed:

Bug 1: "do you refer to the knowledge graph at all?" - board_briefing.py's
relevance scorer split module paths only on "." and "/", so a founder's
two-word phrase ("knowledge graph") could never match the compound,
underscore-joined directory app/platform/architecture_knowledge_graph/ - while
an unrelated single-word package, app/platform/knowledge/ (Knowledge Vault),
coincidentally matched instead. Jarvis wasn't missing the graph; she was
being handed the wrong package's modules.

Bug 2: a request to evaluate agent skills against an external list got a
disconnected, generic "strongest customer evidence... bounded proof" non-
answer. Root cause: conversation_mode.py's product_review regex matched the
bare word "agents?" alone (documented as a defect in PR #500's own commit
message but never actually fixed there - only worked around for one specific
message shape), misrouting an analytical request into a mode that
context_retriever.py doesn't give the agent roster to, and
founder_response_composer.py's STRATEGIC_ADVICE quality gate discarded any
draft lacking one of five hardcoded words, substituting the canned fallback
regardless of how good the real answer was.
"""

BUG_1_QUESTION = "do you refer to the knowledge graph at all? if yes, when do you do that?"
BUG_2_QUESTION = (
    "Jarvis, can you evaluate if any of our agents has these skills as [named external GitHub repo] "
    "if we do not have please make a list of all the skills that we do not have and map out which "
    "agents need to have these skills"
)


def _check_bug_1_relevance_selection() -> None:
    result = build_architecture_graph_briefing(BUG_1_QUESTION)
    assert result["status"] == "ready", result
    modules = [item["module"] for item in result["modules"]]
    assert modules, "no modules selected at all"
    assert all(module.startswith("app.platform.architecture_knowledge_graph") for module in modules), modules
    assert not any(module.startswith("app.platform.knowledge.") for module in modules), (
        "selected the unrelated Knowledge Vault package instead of the architecture graph itself: %s" % modules
    )


def _check_bug_2_mode_classification() -> None:
    decomposition = RequestDecomposer().decompose(BUG_2_QUESTION)
    mode_decision = ConversationModeClassifier.classify(BUG_2_QUESTION, decomposition)
    assert mode_decision.mode != "product_review", (
        "bare 'agents?' in the product_review regex misclassified an analytical request again"
    )


def _check_bug_2_context_includes_organisation() -> None:
    from app.platform.board_room.context_retriever import ContextRetriever

    for mode in ("product_review", "executive_discussion", "strategic_advice", "brainstorming"):
        assert "organisation" in ContextRetriever._source_names(mode), (
            "%s mode has no access to the agent roster/skills data" % mode
        )


def _check_bug_2_honest_draft_survives_quality_gate() -> None:
    """The exact regression: a realistic, honest, on-topic draft that explains
    the external-fetch limitation and attempts the answerable part must not be
    discarded and replaced with the generic canned fallback."""
    realistic_draft = (
        "I cannot fetch an external GitHub repository directly, so I cannot pull that list myself - "
        "you would need to paste the skill names here for me to compare. Based on our current agent "
        "roster, backend_manager_agent, frontend_manager_agent, and database_manager_agent cover "
        "domain-specific review skills, and reviewer_agent covers independent review. I do not see "
        "any agent with a documented skill for security scanning, so if that is on your list, I would "
        "suggest adding it to backend_manager_agent next, since backend code is where that risk "
        "concentrates most."
    )
    contract = FounderConversationContract._contract("STRATEGIC_ADVICE", "Make a decision-ready recommendation", False)
    signals = FounderResponseComposer._quality_signals(realistic_draft, BUG_2_QUESTION, contract)
    assert not signals, ("a substantive, honest, on-topic draft was still discarded: %s" % (signals,))


def _check_bug_2_full_pipeline() -> None:
    """End-to-end: with a mocked LLM returning the realistic draft above, the
    real board_room_chat pipeline must return that draft, not the canned
    'strongest customer evidence...bounded proof' fallback."""
    from app.platform.operating_console.service import board_room_chat

    realistic_draft = (
        "I cannot fetch an external GitHub repository directly, so I cannot pull that list myself - "
        "you would need to paste the skill names here for me to compare. Based on our current agent "
        "roster, backend_manager_agent, frontend_manager_agent, and database_manager_agent cover "
        "domain-specific review skills, and reviewer_agent covers independent review. I do not see "
        "any agent with a documented skill for security scanning, so if that is on your list, I would "
        "suggest adding it to backend_manager_agent next, since backend code is where that risk "
        "concentrates most."
    )

    def _authorized(_payload):
        return {"authorized": True, "email": "founder@example.com"}

    def _mock_ai(_payload):
        return {"status": "completed", "output_text": realistic_draft}

    with patch("app.platform.operating_console.service.require_founder", _authorized), patch(
        "app.platform.operating_console.service.invoke_ai", _mock_ai
    ):
        result = board_room_chat({
            "token": "founder", "message": BUG_2_QUESTION,
            "provider": "deepseek", "model": "deepseek-v4-pro",
        })
    assert result["board_room_response"] == realistic_draft, result["board_room_response"]
    assert "strongest customer evidence" not in result["board_room_response"]


def main() -> None:
    create_platform_tables()
    _check_bug_1_relevance_selection()
    _check_bug_2_mode_classification()
    _check_bug_2_context_includes_organisation()
    _check_bug_2_honest_draft_survives_quality_gate()
    _check_bug_2_full_pipeline()
    print("JARVIS LIVE BUG REGRESSION CHECK PASSED")


if __name__ == "__main__":
    main()
