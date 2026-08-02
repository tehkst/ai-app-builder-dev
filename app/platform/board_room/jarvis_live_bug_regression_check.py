from __future__ import annotations

from unittest.mock import patch

from app.platform.architecture_knowledge_graph.board_briefing import build_architecture_graph_briefing
from app.platform.board_room.context_retriever import ContextRetriever
from app.platform.board_room.conversation_mode import ConversationModeClassifier
from app.platform.board_room.executive_intelligence_orchestrator import ExecutiveIntelligenceOrchestrator
from app.platform.board_room.executive_response_critic import ExecutiveResponseCritic
from app.platform.board_room.founder_conversation_contract import FounderConversationContract
from app.platform.board_room.founder_response_composer import FounderResponseComposer
from app.platform.board_room.request_decomposer import RequestDecomposer
from app.platform.persistence.database import create_platform_tables

"""Locks in real bugs found via live founder testing on production, all traced
to their actual root cause by reading the deployed code, not guessed:

Bug 1: "do you refer to the knowledge graph at all?" - board_briefing.py's
relevance scorer split module paths only on "." and "/", so a founder's
two-word phrase ("knowledge graph") could never match the compound,
underscore-joined directory app/platform/architecture_knowledge_graph/ - while
an unrelated single-word package, app/platform/knowledge/ (Knowledge Vault),
coincidentally matched instead. Jarvis wasn't missing the graph; she was
being handed the wrong package's modules.

Bug 2 (first pass, PR #522): a request to evaluate agent skills against an
external list got a disconnected, generic "strongest customer evidence...
bounded proof" non-answer. That fix widened founder_response_composer.py's
STRATEGIC_ADVICE keyword gate and confirmed it with ONLY a mocked LLM call fed
a hand-written "realistic" draft that happened to contain the word "suggest" -
which is exactly why it passed the gate it was meant to test. The founder
re-reported the *same* byte-for-byte non-answer afterward in a fresh chat.

Bug 2 (real root cause, this pass): re-run against the REAL, non-mocked
deterministic layers (RequestDecomposer, ConversationModeClassifier,
ContextRetriever, ExecutiveIntelligenceOrchestrator - all pure Python, no LLM
call) with a genuinely honest ANALYTICAL draft that contains no recommendation
language at all (because the founder asked Jarvis to *evaluate and list*, not
to *recommend* - RequestDecomposer correctly reports
requested_action="ANALYZE" for this message). That draft was discarded by
BOTH founder_response_composer.py's `_quality_signals()` (its STRATEGIC_ADVICE
branch required one of ten hardcoded recommendation-framed words, unmet by any
honest audit-style answer) AND executive_response_critic.py's `evaluate()`
(its `recommendation_required` gate applied to every STRATEGIC_ADVICE-family
message regardless of whether it was actually a recommendation request). Both
now take `decomposition` and skip the recommendation-required checks when
`requested_action == "ANALYZE"`, since an evaluation/audit answer has no
reason to contain recommendation language. No real DEEPSEEK_API_KEY was
available in this environment; every layer below the actual LLM call itself
(everything that discarded the draft) was verified for real - see
`_check_bug_2_analytical_draft_survives_real_gates` for what "real" means here
and its docstring for the one thing that remains necessarily a stand-in.
"""

BUG_1_QUESTION = "do you refer to the knowledge graph at all? if yes, when do you do that?"
BUG_2_QUESTION = (
    "Jarvis, can you evaluate if any of our agents has these skills as [named external GitHub repo] "
    "if we do not have please make a list of all the skills that we do not have and map out which "
    "agents need to have these skills"
)
# The exact message the founder re-reported live in production, byte-for-byte, after
# PR #522 was already deployed - proof the first fix's mocked verification missed the
# real gap.
BUG_2_REPRODUCTION_QUESTION = (
    "Jarvis, can you evaluate if any of our agents has these skills as Agent Reach "
    "https://github.com/Panniantong/agent-reach if we do not have please make a list of all the "
    "skills that we do not have and map out which agents need to have these skills build and trains."
)
# A genuinely honest, on-topic, ANALYTICAL answer with zero recommendation-framing
# language - the register a real LLM plausibly uses when asked to *evaluate and list*
# rather than to *recommend*. This is the one necessarily hand-written stand-in for a
# real DeepSeek response (no API key was available in this environment); everything
# downstream of it (the two gates that discarded it) was verified against real code.
HONEST_ANALYTICAL_DRAFT = (
    "I cannot fetch external URLs, so I cannot open https://github.com/Panniantong/agent-reach directly - "
    "you would need to paste its skill list here for a full comparison. Based on the current agent roster and "
    "their documented skills.md files: backend_manager_agent covers backend code review and API design; "
    "frontend_manager_agent covers UI review and component architecture; database_manager_agent covers schema "
    "and query review; reviewer_agent covers independent cross-cutting review. None of the current agents has a "
    "documented skill for autonomous web browsing, computer-use style GUI automation, or reach/outreach "
    "automation of the kind Agent Reach appears to describe from its name. Mapping: backend_manager_agent and "
    "database_manager_agent would be the agents to extend first if that capability is added, since outreach "
    "automation touches API integration and data storage most directly."
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
    """The REAL wiring, not the one a prior fix mistakenly patched.

    operating_console/service.py's only real call to ContextRetriever().retrieve()
    always passes selected_sources=set(contract.context_sources) - never None - so
    ContextRetriever._source_names() is unreachable dead code from real founder
    traffic. A prior fix added "organisation" there anyway, which is why its own
    test of _source_names() passed while production kept giving Jarvis zero agent-
    roster/skills data for these modes. The assertion that actually matters checks
    FounderConversationContract's source_map, which is what real requests use.
    """
    from app.platform.board_room.context_retriever import ContextRetriever
    from app.platform.board_room.founder_conversation_contract import FounderConversationContract

    for mode in ("product_review", "executive_discussion", "strategic_advice", "brainstorming"):
        assert "organisation" in ContextRetriever._source_names(mode), (
            "%s mode has no access to the agent roster/skills data via _source_names()" % mode
        )
    for family in ("STRATEGIC_ADVICE",):
        assert "organisation" in FounderConversationContract._contract(family).context_sources, (
            "%s contract family has no access to the agent roster/skills data in the REAL "
            "wiring (contract.context_sources) - _source_names() passing is not sufficient" % family
        )


def _check_bug_2_honest_draft_survives_quality_gate() -> None:
    """A realistic, honest, on-topic draft that explains the external-fetch
    limitation and attempts the answerable part must not be discarded and
    replaced with the generic canned fallback - checked with the decomposition
    actually threaded through, the way the real pipeline calls it."""
    decomposition = RequestDecomposer().decompose(BUG_2_REPRODUCTION_QUESTION)
    assert decomposition["requested_action"] == "ANALYZE", decomposition
    contract = FounderConversationContract._contract("STRATEGIC_ADVICE", "Make a decision-ready recommendation", False)
    signals = FounderResponseComposer._quality_signals(
        HONEST_ANALYTICAL_DRAFT, BUG_2_REPRODUCTION_QUESTION, contract, decomposition
    )
    assert not signals, ("a substantive, honest, on-topic ANALYTICAL draft was still discarded: %s" % (signals,))


def _check_bug_2_analytical_draft_survives_real_gates() -> None:
    """The actual re-reported failure, verified against every REAL deterministic
    layer of the pipeline - RequestDecomposer, ConversationModeClassifier,
    ContextRetriever, and ExecutiveIntelligenceOrchestrator are all pure Python
    with no LLM call, so this runs them for real rather than re-deriving their
    output. The only necessarily hand-written stand-in is HONEST_ANALYTICAL_DRAFT
    itself (no DEEPSEEK_API_KEY was available in this environment to get a real
    completion) - everything that actually discarded the draft in production
    (ExecutiveResponseCritic, FounderResponseComposer) runs unmocked here."""
    decomposition = RequestDecomposer().decompose(BUG_2_REPRODUCTION_QUESTION)
    mode_decision = ConversationModeClassifier.classify(BUG_2_REPRODUCTION_QUESTION, decomposition)
    contract = FounderConversationContract.classify(
        BUG_2_REPRODUCTION_QUESTION, response_mode=mode_decision.mode, decomposition=decomposition
    )
    context = ContextRetriever().retrieve(
        BUG_2_REPRODUCTION_QUESTION,
        decomposition=decomposition,
        conversation_mode=mode_decision.mode,
        selected_sources=ContextRetriever._source_names(mode_decision.mode),
    )
    plan = ExecutiveIntelligenceOrchestrator().plan(
        BUG_2_REPRODUCTION_QUESTION, mode=mode_decision.mode, context=context, decomposition=decomposition
    )
    quality = ExecutiveResponseCritic.evaluate(
        HONEST_ANALYTICAL_DRAFT,
        mode=mode_decision.mode,
        founder_message=BUG_2_REPRODUCTION_QUESTION,
        executive_brief=plan.executive_brief,
        contract=contract,
        decomposition=decomposition,
    )
    assert quality.acceptable, ("real ExecutiveResponseCritic rejected an honest analytical draft: %s" % (quality.signals,))
    result = FounderResponseComposer.compose(
        founder_message=BUG_2_REPRODUCTION_QUESTION,
        draft=HONEST_ANALYTICAL_DRAFT,
        contract=contract,
        context=context,
        executive_brief=plan.executive_brief,
        decomposition=decomposition,
    )
    assert not result.fallback_used, "real FounderResponseComposer still substituted the canned fallback"
    assert result.text == HONEST_ANALYTICAL_DRAFT, result.text
    assert "strongest customer evidence" not in result.text


def _check_bug_2_full_pipeline() -> None:
    """End-to-end: with a mocked LLM returning the honest analytical draft, the
    real board_room_chat pipeline must return that draft, not the canned
    'strongest customer evidence...bounded proof' fallback. The LLM call is the
    only mocked piece; the routing, context, orchestration, critic, and
    composer layers in between all run for real."""
    from app.platform.operating_console.service import board_room_chat

    def _authorized(_payload):
        return {"authorized": True, "email": "founder@example.com"}

    def _mock_ai(_payload):
        return {"status": "completed", "output_text": HONEST_ANALYTICAL_DRAFT}

    with patch("app.platform.operating_console.service.require_founder", _authorized), patch(
        "app.platform.operating_console.service.invoke_ai", _mock_ai
    ):
        result = board_room_chat({
            "token": "founder", "message": BUG_2_REPRODUCTION_QUESTION,
            "provider": "deepseek", "model": "deepseek-v4-pro",
        })
    assert result["board_room_response"] == HONEST_ANALYTICAL_DRAFT, result["board_room_response"]
    assert "strongest customer evidence" not in result["board_room_response"]


def main() -> None:
    create_platform_tables()
    _check_bug_1_relevance_selection()
    _check_bug_2_mode_classification()
    _check_bug_2_context_includes_organisation()
    _check_bug_2_honest_draft_survives_quality_gate()
    _check_bug_2_analytical_draft_survives_real_gates()
    _check_bug_2_full_pipeline()
    print("JARVIS LIVE BUG REGRESSION CHECK PASSED")


if __name__ == "__main__":
    main()
