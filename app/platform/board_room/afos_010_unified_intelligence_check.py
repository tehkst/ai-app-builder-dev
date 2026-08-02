from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.platform.board_room.cognitive_core import JarvisCognitiveCore
from app.platform.board_room.executive_intelligence_orchestrator import (
    ExecutiveIntelligenceOrchestrator,
)
from app.platform.board_room.request_decomposer import RequestDecomposer


def _context() -> dict[str, Any]:
    return {
        "sources": {
            "executive_intelligence": {"status": "executive-state-ready"},
            "company_memory": {"status": "integrated"},
            "repository_intelligence": {"status": "repository-intelligence-ready"},
        },
        "source_status": {
            "executive_intelligence": "executive-state-ready",
            "company_memory": "integrated",
            "repository_intelligence": "repository-intelligence-ready",
        },
        "observations": {
            "active_missions": 0,
            "blocked_missions": 0,
            "repository_areas_available": 10,
        },
    }


def _reasoning() -> dict[str, Any]:
    return {
        "intent": "Choose the strongest company direction",
        "decision_requested": "choose between competing investments",
        "recommendation": {
            "action": "Focus on the executive software factory",
            "why": "It compounds the company's differentiated governance and delivery strengths.",
            "confidence": "medium",
        },
        "alternatives": [
            {
                "option": "Copy a coding workspace",
                "trade_off": "Faster familiarity but weaker differentiation",
                "criteria": {"strategic coherence": 2},
            },
            {
                "option": "Build the executive software factory",
                "trade_off": "Harder product design but stronger differentiation",
                "criteria": {"strategic coherence": 5},
            },
        ],
        "evidence": [{"fact": "Governed delivery capabilities already exist", "source": "Executive Intelligence"}],
        "uncertainty": ["Customer preference evidence is unavailable."],
        "risk": {"level": "medium", "factors": ["positioning evidence is incomplete"]},
        "impact": "A coherent category position improves founder focus and product differentiation.",
        "consequence_of_inaction": "The product risks resembling a collection of coding features.",
        "confidence": "medium",
        "request_decomposition": {"requested_action": "COMPARE", "dominant_goal": "compare_options"},
        "evaluation_criteria": [{"name": "strategic coherence"}],
        "estimated_effort": "Small",
        "next_action": "Continue the strategic discussion.",
        "governance": {"required": False},
        "presentation_mode": "comparison",
    }


class _Generator:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        return _reasoning()


def main() -> None:
    advisory = ExecutiveIntelligenceOrchestrator()
    generator = _Generator()
    advisory.recommendation_generator = generator  # type: ignore[assignment]
    decomposition = RequestDecomposer().decompose(
        "Should we become more like Replit or focus on being an executive software factory?"
    )
    plan = advisory.plan(
        "Should we become more like Replit or focus on being an executive software factory?",
        mode="strategic_advice",
        context=_context(),
        decomposition=decomposition,
    )
    assert generator.calls == 1
    assert plan.uses_decision_engine and plan.strategy == "COMPARE"
    assert plan.executive_brief["recommended_position"]
    assert plan.executive_brief["verified_evidence"]
    assert plan.executive_brief["unknowns"]
    assert len(plan.executive_brief["perspective_contributions"]) <= 3
    assert plan.executive_brief["governance"] == {
        "read_only": True,
        "execution_allowed": False,
        "mission_creation_allowed": False,
    }

    direct = ExecutiveIntelligenceOrchestrator()
    direct_generator = _Generator()
    direct.recommendation_generator = direct_generator  # type: ignore[assignment]
    direct_plan = direct.plan(
        "Explain how Mission Execution works.",
        mode="explanation",
        context=_context(),
        decomposition=RequestDecomposer().decompose("Explain how Mission Execution works."),
    )
    assert direct_generator.calls == 0
    assert direct_plan.depth_tier == 0 and not direct_plan.uses_decision_engine

    provider_calls: list[dict[str, Any]] = []

    def healthy_provider(payload: dict[str, Any]) -> dict[str, Any]:
        provider_calls.append(payload)
        return {
            "status": "completed",
            "output_text": (
                "Focus on the executive software factory. Governed delivery already exists, and it gives the company "
                "a differentiated position. Copying a coding workspace offers faster familiarity, but sacrifices strategic "
                "coherence. Customer preference remains unknown, so validate the position before making an irreversible bet."
            ),
        }

    original_plan = ExecutiveIntelligenceOrchestrator.plan

    def fixed_plan(self: ExecutiveIntelligenceOrchestrator, *_args: Any, **_kwargs: Any):
        return plan

    ExecutiveIntelligenceOrchestrator.plan = fixed_plan  # type: ignore[method-assign]
    try:
        answer = JarvisCognitiveCore.respond(
            founder_message="Which direction should we choose?",
            mode="strategic_advice",
            context=_context(),
            invoke=healthy_provider,
            decomposition=decomposition,
        )
    finally:
        ExecutiveIntelligenceOrchestrator.plan = original_plan  # type: ignore[method-assign]
    assert len(provider_calls) == 1
    assert answer.startswith("Focus on the executive software factory")
    prompt = provider_calls[0]["prompt"]
    assert "Executive brief" in prompt and "recommended_position" in prompt

    rejected_calls: list[dict[str, Any]] = []

    def rejected_provider(payload: dict[str, Any]) -> dict[str, Any]:
        rejected_calls.append(payload)
        return {"status": "completed", "output_text": "Maybe."}

    ExecutiveIntelligenceOrchestrator.plan = fixed_plan  # type: ignore[method-assign]
    try:
        rejected_answer = JarvisCognitiveCore.respond(
            founder_message="Which direction should we choose?",
            mode="strategic_advice",
            context=_context(),
            invoke=rejected_provider,
            decomposition=decomposition,
        )
    finally:
        ExecutiveIntelligenceOrchestrator.plan = original_plan  # type: ignore[method-assign]
    assert len(rejected_calls) == 2
    assert "Bounded revision instruction" in rejected_calls[1]["prompt"]
    assert rejected_answer != plan.fallback_response
    assert "could not produce a verified, reviewed answer" in rejected_answer
    assert "Verified evidence:" not in rejected_answer
    assert "project progress:" not in rejected_answer

    serialized = json.dumps({"answer": answer})
    for forbidden in (
        "executive_brief", "perspective_contributions", "option scores",
        "technical_details", "route score", "system prompt",
    ):
        assert forbidden not in serialized

    cognitive_source = Path(__file__).with_name("cognitive_core.py").read_text()
    assert "ExecutiveDecisionEngine(" not in cognitive_source
    assert "create_mission" not in cognitive_source
    assert "run_console_workflow" not in cognitive_source
    print("AFOS-010 unified executive intelligence checks passed")


if __name__ == "__main__":
    main()
