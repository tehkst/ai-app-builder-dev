from __future__ import annotations

from typing import Any

from app.platform.board_room.executive_reasoning_engine import ExecutiveReasoningEngine


BEHAVIOR_CASES = [
    ("Implement a small UI polish mission.", "implementation_handoff"),
    ("Should we deploy the current revision to production?", "structured"),
    ("Should we prioritize growth or platform reliability?", "structured"),
    ("Should we focus on fundraising or customer retention?", "structured"),
    ("Why are engineering missions taking too long?", "structured"),
    ("What should we improve next?", "structured"),
    ("Critique our current product strategy.", "structured"),
    ("Build a 90-day execution strategy.", "structured"),
    ("What work should we stop?", "structured"),
]
UNSEEN_CASES = [
    "We have limited engineering capacity. Should we fix technical debt or build the investor demo?",
    "Why do we keep adding capabilities but still feel unfinished?",
    "What should I stop building?",
]
BANNED_FOUNDER_TERMS = (
    "branch:",
    "compileall",
    "engineering worker implementation handoff",
    "json payload",
    "route:",
)


def _context() -> dict[str, Any]:
    return {
        "source_status": {
            "company_intelligence": "company-intelligence-ready",
            "company_memory": "integrated",
            "mission_history": "mission-pipeline-observer-ready",
            "repository_intelligence": "repository-intelligence-ready",
            "engineering_capacity": "engineering-manager-ready",
        },
        "sources": {
            "company_intelligence": {"status": "company-intelligence-ready"},
            "company_memory": {"status": "integrated"},
            "mission_history": {"status": "mission-pipeline-observer-ready"},
            "repository_intelligence": {"status": "repository-intelligence-ready"},
            "engineering_capacity": {"status": "engineering-manager-ready"},
        },
        "observations": {
            "platform_stage": "approval-gated AI engineering operating system",
            "estimated_completion_percent": 68,
            "active_missions": 1,
            "blocked_missions": 0,
            "repository_areas_available": 10,
            "engineering_mode": "planning-management-only",
            "engineering_requires_founder_approval": True,
            "pipeline_observer_only": True,
        },
    }


def _reason(prompt: str, response_mode: str = "structured") -> dict[str, Any]:
    engine = ExecutiveReasoningEngine()
    engine.context_retriever.retrieve = lambda *_args, **_kwargs: _context()
    return engine.reason(prompt, response_mode=response_mode)


def main() -> None:
    behavior_results = [_reason(prompt, mode) for prompt, mode in BEHAVIOR_CASES]
    presentation_modes = {
        result["reasoning"]["presentation_mode"]
        for result in behavior_results
    }
    assert presentation_modes == {
        "comparison",
        "prioritization",
        "diagnosis",
        "critique",
        "roadmap",
        "execution",
        "governed_action",
    }, presentation_modes
    signatures = {
        (
            result["reasoning"]["decision_requested"],
            result["reasoning"]["recommendation"]["action"],
        )
        for result in behavior_results
    }
    assert len(signatures) >= 8, signatures

    for result in behavior_results:
        reasoning = result["reasoning"]
        assert reasoning["evaluation_criteria"]
        assert reasoning["evidence"]
        assert len(reasoning["alternatives"]) >= 2
        assert reasoning["uncertainty"]
        visible = result["founder_response"].lower()
        assert not any(term in visible for term in BANNED_FOUNDER_TERMS)

    unseen_results = [_reason(prompt) for prompt in UNSEEN_CASES]
    unseen_signatures = {
        (
            result["reasoning"]["decision_requested"],
            result["reasoning"]["recommendation"]["action"],
        )
        for result in unseen_results
    }
    assert len(unseen_signatures) == len(UNSEEN_CASES), unseen_signatures
    assert [result["reasoning"]["presentation_mode"] for result in unseen_results] == [
        "comparison",
        "diagnosis",
        "critique",
    ]
    assert "smallest credible investor demo" in unseen_results[0]["founder_response"].lower()
    assert "completion and coherence constraint" in unseen_results[1]["founder_response"].lower()
    assert "starting net-new" in unseen_results[2]["founder_response"].lower()
    print("executive decision engine behavior ok")


if __name__ == "__main__":
    main()
