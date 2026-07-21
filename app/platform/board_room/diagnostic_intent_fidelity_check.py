from __future__ import annotations

import json

from app.platform.board_room.executive_reasoning_engine import ExecutiveReasoningEngine


MISSION_ID = "MISSION-DA587720B8B6"


def run_check() -> dict[str, object]:
    engine = ExecutiveReasoningEngine()
    request = (
        f"Present the preserved runtime failure evidence for {MISSION_ID}. "
        "Show the complete change-set validation report and identify missing evidence."
    )
    result = engine.reason(request, response_mode="clarify")
    reasoning = result.get("reasoning") or {}
    evidence = reasoning.get("diagnostic_evidence") or {}
    response = str(result.get("founder_response") or "")

    assert reasoning.get("intent") == "diagnostic_evidence_retrieval"
    assert reasoning.get("presentation_mode") == "diagnostic_evidence"
    assert evidence.get("mission_id") == MISSION_ID
    assert evidence.get("governance", {}).get("stores_state") is False
    assert evidence.get("governance", {}).get("creates_new_retrieval_system") is False
    assert evidence.get("governance", {}).get("recommendation_ranking_bypassed") is True
    assert "I recommend making" not in response
    assert "Diagnostic evidence retrieval" in response
    assert "Sources inspected:" in response
    assert "Supported conclusion:" in response

    normal = engine.reason("What should we improve next?", response_mode="recommend")
    normal_reasoning = normal.get("reasoning") or {}
    assert normal_reasoning.get("intent") != "diagnostic_evidence_retrieval"

    return {
        "milestone": "MC-JARVIS-02",
        "status": "passed",
        "mission_id": MISSION_ID,
        "routing": "evidence-before-recommendation",
        "reuse_policy": "existing-context-sources-only",
        "evidence_status": evidence.get("evidence_status"),
    }


if __name__ == "__main__":
    print(json.dumps(run_check(), indent=2, sort_keys=True))
