from __future__ import annotations

from app.platform.board_room.context_retriever import ContextRetriever
from app.platform.board_room.executive_reasoning_engine import ExecutiveReasoningEngine


MISSION_ID = "MISSION-DA587720B8B6"


def _sample_sources() -> dict:
    return {
        "executive_intelligence": {
            "status": "executive-intelligence-ready",
            "active_mission": {
                "value": {
                    "mission_id": MISSION_ID,
                    "workflow_run_id": "MISSION-RUN-TEST",
                    "blocking_reason": "change_set_validation_failure",
                }
            },
        },
        "mission_history": {
            "status": "mission-pipeline-observer-ready",
            "missions": [
                {
                    "mission_id": "MISSION-CONTROL-001",
                    "synthetic": True,
                }
            ],
        },
        "company_memory": {"status": "ready"},
        "repository_intelligence": {"status": "ready"},
        "engineering_capacity": {"status": "ready"},
    }


def run_check() -> dict:
    continuity = ContextRetriever._executive_continuity(
        _sample_sources(),
        "Please identify the exact durable source record.",
        "decision_support",
    )
    assert continuity["has_context"] is True
    assert continuity["mission_id"] == MISSION_ID
    assert continuity["workflow_run_id"] == "MISSION-RUN-TEST"
    assert continuity["blocking_reason"] == "change_set_validation_failure"
    assert continuity["pipeline_linked"] is False
    assert continuity["degraded"] is True

    reasoning = {
        "request_decomposition": {
            "dominant_goal": "clarify",
            "lifecycle_context": "decision_support",
        },
        "recommendation": {
            "action": "Clarify the desired business outcome",
            "why": "The request was classified as unclear.",
        },
        "next_action": "Ask a generic clarification question.",
        "evidence": [],
        "technical_details": {},
    }
    ExecutiveReasoningEngine._enforce_context_continuity(
        reasoning,
        {"executive_continuity": continuity},
        response_mode="clarify",
    )

    assert reasoning["request_decomposition"]["dominant_goal"] == "analyze_existing"
    assert MISSION_ID in reasoning["recommendation"]["action"]
    assert "generic clarification" not in reasoning["next_action"].lower()
    assert reasoning["technical_details"]["executive_context_continuity"]["has_context"] is True

    return {
        "milestone": "MC-JARVIS-01",
        "status": "passed",
        "mission_id": MISSION_ID,
        "continuity_mode": continuity["mode"],
        "fallback_policy": continuity["fallback_policy"],
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_check(), indent=2, sort_keys=True))
