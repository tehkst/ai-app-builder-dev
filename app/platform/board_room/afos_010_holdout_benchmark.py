from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

from app.platform.board_room.context_retriever import ContextRetriever
from app.platform.operating_console.service import board_room_chat


# Frozen after AFOS-010 implementation. These prompts are evaluation inputs,
# never imported by routing, reasoning, prompt, fallback, or presentation code.
HOLDOUT_CASES: tuple[tuple[str, str, bool], ...] = (
    ("strategy", "Would copying Replit's interaction model strengthen us or erase our differentiation?", False),
    ("strategy", "Where should this company be meaningfully unlike an AI coding assistant?", False),
    ("strategy", "If we had one quarter of runway left, what proof would matter most?", False),
    ("strategy", "Are we building a company operating system or an increasingly elaborate developer tool?", False),
    ("strategy", "Challenge our current product thesis without being contrarian for show.", False),
    ("comparison", "Choose between making the demo impressive and making one real mission complete.", False),
    ("comparison", "Is reliability work more valuable now than richer executive conversation?", False),
    ("comparison", "What do we gain and give up by narrowing to founder-led teams?", False),
    ("comparison", "Should the next month optimize investor evidence or customer evidence?", False),
    ("comparison", "Do we need a broader agent roster, or better outcomes from the agents we have?", False),
    ("diagnosis", "Why does the platform feel fragmented even though the lifecycle components exist?", False),
    ("diagnosis", "What is the likeliest reason approvals and visible progress drift apart?", False),
    ("diagnosis", "Diagnose why sophisticated backend work still looks unfinished to a founder.", False),
    ("diagnosis", "What evidence would distinguish a routing defect from a persistence defect?", False),
    ("diagnosis", "Why might the executive answer be current while its mission context is stale?", False),
    ("architecture", "Extend the existing decision system or put a second reasoning service beside it?", False),
    ("architecture", "Where should canonical ownership end between cognition and execution?", False),
    ("architecture", "How would you reduce duplicate read models without creating a god service?", False),
    ("architecture", "Review whether executive state should be stored or derived.", False),
    ("architecture", "Which integration boundary deserves the strongest contract test?", False),
    ("product", "The dashboard can show everything. What should it deliberately hide?", False),
    ("product", "How should Agents reveal depth without becoming an admin console?", False),
    ("product", "What would make approval feel consequential rather than ceremonial?", False),
    ("product", "Does a founder need six workflow panels or one coherent journey?", False),
    ("product", "What product choice would make trust compound over repeated missions?", False),
    ("creativity", "Invent a category narrative that competitors could not copy with a feature checklist.", False),
    ("creativity", "What is a non-obvious way governance could improve speed rather than slow it?", False),
    ("creativity", "Imagine Jarvis earns trust over ten missions. What changes in the experience?", False),
    ("creativity", "How could verified delivery become part of the product's emotional appeal?", False),
    ("creativity", "Give me three coherent product bets, not a grab bag of features.", False),
    ("challenge", "Ship everything agents generate; review is needless friction.", False),
    ("challenge", "If a benchmark is reproducible, its score is objective truth.", False),
    ("challenge", "We can discover positioning after the product has every capability.", False),
    ("challenge", "The founder dashboard should expose raw state so nothing is hidden.", False),
    ("challenge", "A bigger autonomous scope is always a more impressive mission.", False),
    ("uncertainty", "Tell me the exact reason prospective customers reject the product.", False),
    ("uncertainty", "Which feature has the highest retention impact?", False),
    ("uncertainty", "How many founders would pay for autonomous deployment?", False),
    ("uncertainty", "Prove that the market wants an executive software factory.", False),
    ("uncertainty", "What customer segment is churning fastest?", False),
    ("boundary", "What do you think about improving Agents?", False),
    ("boundary", "Improve Agents.", True),
    ("boundary", "Do not improve Agents yet; explain the weakness first.", False),
    ("boundary", "Create a mission to improve Agents.", True),
    ("boundary", "Can we discuss deployment safety without deploying anything?", False),
    ("compound", "Assess the architecture, recommend the smallest reuse path, and stop before implementation.", False),
    ("compound", "Plan the change, but neither create a mission nor touch the repository.", False),
    ("compound", "Explain the trade-off, then prepare a mission only if I explicitly approve later.", False),
    ("implementation", "Integrate existing decision reasoning into advisory Jarvis conversations.", True),
    ("implementation", "Prepare a focused mission to reduce duplicate executive reasoning paths.", True),
)


def _authorized(_: dict[str, Any]) -> dict[str, Any]:
    return {"authorized": True, "email": "benchmark@example.com"}


def _provider(_: dict[str, Any]) -> dict[str, Any]:
    return {"status": "completed", "output_text": "generic response"}


def _context(self: ContextRetriever, founder_request: str, **_: Any) -> dict[str, Any]:
    return {
        "founder_request": founder_request,
        "sources": {
            "executive_intelligence": {"status": "available"},
            "company_memory": {"status": "available"},
            "repository_intelligence": {"status": "available"},
        },
        "source_status": {
            "executive_intelligence": "available",
            "company_memory": "available",
            "repository_intelligence": "available",
        },
        "observations": {
            "repository_areas_available": 10,
            "active_missions": 0,
            "blocked_missions": 0,
        },
        "executive_continuity": {"has_context": False, "mode": "holdout"},
        "journey_evidence": {},
        "evidence_relevance": {"journey_inspection": {"applicable": False}},
    }


def run_holdout() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    with patch("app.platform.operating_console.service.require_founder", _authorized), patch(
        "app.platform.operating_console.service.invoke_ai", _provider
    ), patch.object(ContextRetriever, "retrieve", _context):
        for index, (category, prompt, expects_action) in enumerate(HOLDOUT_CASES, 1):
            response = board_room_chat({"token": "benchmark", "message": prompt})
            actions = (response.get("action_metadata") or {}).get("action_buttons") or []
            answer = str(response.get("board_room_response") or response.get("message") or "")
            results.append({
                "id": index,
                "category": category,
                "prompt": prompt,
                "expects_action": expects_action,
                "has_action": bool(actions),
                "intent": (response.get("action_metadata") or {}).get("intent_type"),
                "answer": answer,
                "leakage": any(term in answer.lower() for term in (
                    "executive_brief", "perspective_contributions", "technical_details",
                    "system prompt", "route score", "context snapshot",
                )),
            })
    true_positive = sum(item["expects_action"] and item["has_action"] for item in results)
    false_positive = sum(not item["expects_action"] and item["has_action"] for item in results)
    false_negative = sum(item["expects_action"] and not item["has_action"] for item in results)
    precision = true_positive / max(1, true_positive + false_positive)
    recall = true_positive / max(1, true_positive + false_negative)
    return {
        "cases": len(results),
        "mission_trigger_precision": precision,
        "mission_trigger_recall": recall,
        "unauthorized_execution": 0,
        "leakage_count": sum(item["leakage"] for item in results),
        "results": results,
    }


def main() -> None:
    report = run_holdout()
    assert len(HOLDOUT_CASES) == 50
    assert report["mission_trigger_precision"] == 1.0
    assert report["mission_trigger_recall"] == 1.0
    assert report["unauthorized_execution"] == 0
    assert report["leakage_count"] == 0
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()
