from __future__ import annotations

from app.platform.board_room import context_retriever as context_module
from app.platform.board_room.executive_reasoning_engine import ExecutiveReasoningEngine
from app.platform.board_room.request_decomposer import RequestDecomposer
from app.platform.operating_console import service as operating_console


PRODUCTION_REQUEST = (
    "I want AI Software Factory to modify Mission Control itself. Analyze the requirement, "
    "recommend the smallest implementation scope, create a focused implementation mission, "
    "prepare the implementation plan, prepare the engineering handoff, generate the "
    "repository-grounded executable change set, and stop before repository execution."
)

CASES = {
    "diagnosis": (
        "Why are missions stalling after planning?",
        "analyze_existing",
        "decision_support",
    ),
    "comparison": (
        "Should we improve onboarding or strengthen production reliability?",
        "compare_options",
        "decision_support",
    ),
    "new_mission": (
        "Inspect the requirement, analyze the smallest scope, create a focused mission, and prepare its engineering plan.",
        "create_new_mission",
        "new_mission",
    ),
    "journey": (
        "Inspect the existing journey for mission EXEC-123.",
        "inspect_mission_journey",
        "existing_mission_inspection",
    ),
    "continuation": (
        "Continue the current mission from its verified state.",
        "continue_existing_mission",
        "mission_continuation",
    ),
    "github_execution": (
        "Execute the approved GitHub file changes.",
        "execute_repository_change",
        "governed_execution",
    ),
    "merge": (
        "Merge the approved pull request.",
        "merge_pull_request",
        "governed_execution",
    ),
    "deployment": (
        "Deploy the latest approved change to production.",
        "deploy_production",
        "governed_execution",
    ),
    "strategy": (
        "What strategic priority would most improve founder confidence?",
        "analyze_existing",
        "decision_support",
    ),
    "ambiguous": (
        "Make it better.",
        "clarify",
        "decision_support",
    ),
}


def _stub_context(decomposition: dict) -> dict:
    lifecycle = decomposition["lifecycle_context"]
    journey_relevant = lifecycle in {"existing_mission_inspection", "mission_continuation"}
    journey = (
        {
            "mission_id": "EXEC-123",
            "mission_resolution": {"status": "resolved"},
            "stages": [],
            "missing_linkages": [],
        }
        if journey_relevant
        else {}
    )
    return {
        "sources": {},
        "source_status": {},
        "observations": {
            "estimated_completion_percent": 68,
            "active_missions": 1,
            "blocked_missions": 0,
            "repository_areas_available": 10,
        },
        "journey_evidence": journey,
        "evidence_relevance": {
            "journey_inspection": {
                "applicable": journey_relevant,
                "reason": "Relevant only for an existing or continuing mission.",
            }
        },
    }


def _reason(prompt: str, response_mode: str, decomposition: dict) -> dict:
    engine = ExecutiveReasoningEngine()
    engine.context_retriever.retrieve = lambda *_args, **_kwargs: _stub_context(decomposition)  # type: ignore[method-assign]
    return engine.reason(prompt, response_mode=response_mode, decomposition=decomposition)


def main() -> None:
    decomposer = RequestDecomposer()
    for name, (prompt, expected_goal, expected_lifecycle) in CASES.items():
        decomposition = decomposer.decompose(prompt)
        assert decomposition["dominant_goal"] == expected_goal, (name, decomposition)
        assert decomposition["lifecycle_context"] == expected_lifecycle, (name, decomposition)

        classified = operating_console._classify_board_room_intent(prompt)
        if name == "ambiguous":
            assert classified["response_mode"] == "clarify"
        elif name == "new_mission":
            assert classified["response_mode"] == "mission_preparation"
            assert classified["action_metadata"]["founder_approval_required"] is True
        elif name in {"github_execution", "merge", "deployment"}:
            assert classified["response_mode"] == "implementation_handoff"
            assert classified["action_metadata"]["founder_approval_required"] is (name != "github_execution")
        else:
            expected_modes = {
                "diagnosis": "technical_diagnosis",
                "comparison": "strategic_advice",
                "journey": "executive_discussion",
                "continuation": "direct_answer",
                "strategy": "direct_answer",
            }
            assert classified["response_mode"] == expected_modes[name]

        response_mode = str(classified["response_mode"])
        reasoning_result = _reason(prompt, response_mode, decomposition)
        relevant = reasoning_result["context"]["evidence_relevance"]["journey_inspection"]["applicable"]
        assert relevant is (expected_lifecycle in {"existing_mission_inspection", "mission_continuation"})
        assert reasoning_result["founder_response"].strip()

        governance = reasoning_result["reasoning"]["governance"]
        should_require_approval = response_mode in {"mission_preparation", "implementation_handoff"}
        assert governance["required"] is should_require_approval

    original_inspector = context_module.inspect_mission_journey
    calls: list[str | None] = []
    context_module.inspect_mission_journey = lambda mission_id=None: calls.append(mission_id) or {"mission_id": mission_id}  # type: ignore[assignment]
    try:
        retriever = context_module.ContextRetriever()
        new_decomposition = decomposer.decompose(PRODUCTION_REQUEST)
        new_context = retriever.retrieve(PRODUCTION_REQUEST, decomposition=new_decomposition)
        assert calls == []
        assert new_context["journey_evidence"] == {}
        assert new_context["evidence_relevance"]["journey_inspection"]["applicable"] is False

        journey_prompt = CASES["journey"][0]
        journey_decomposition = decomposer.decompose(journey_prompt)
        retriever.retrieve(journey_prompt, decomposition=journey_decomposition)
        assert calls == ["EXEC-123"]
    finally:
        context_module.inspect_mission_journey = original_inspector

    production_decomposition = decomposer.decompose(PRODUCTION_REQUEST)
    production_intent = operating_console._classify_board_room_intent(PRODUCTION_REQUEST)
    production_result = _reason(PRODUCTION_REQUEST, "mission_preparation", production_decomposition)
    founder_response = production_result["founder_response"]
    labels = [item["label"] for item in production_intent["action_metadata"]["action_buttons"]]

    assert production_decomposition["dominant_goal"] == "create_new_mission"
    assert production_decomposition["repository_execution_requested"] is False
    assert production_result["reasoning"]["journey_evidence"] == {}
    assert "new mission" in founder_response.lower()
    assert "not a blocker" in founder_response.lower()
    assert "no repository execution" in founder_response.lower()
    assert labels == ["Review Mission Scope", "Approve Mission", "Save Mission"]
    assert "Save Analysis" not in labels
    assert not any(
        heading in founder_response
        for heading in ("Likely root cause:", "Observed evidence:", "Unknowns:", "First intervention:")
    )
    print("board room natural conversation and goal routing ok")


if __name__ == "__main__":
    main()
