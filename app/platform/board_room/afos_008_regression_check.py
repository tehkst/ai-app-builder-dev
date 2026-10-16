from __future__ import annotations

import json
from unittest.mock import patch

from app.platform.board_room.execution_first_policy import ExecutionFirstPolicy
from app.platform.board_room.request_decomposer import RequestDecomposer
from app.platform.operating_console.action_service import (
    build_decision_ready_mission_actions,
    dispatch_board_room_action,
)
from app.platform.operating_console.service import board_room_chat
from app.platform.ui.mission_control import render_dashboard


CAPABILITY_PROMPT = "Jarvis tell me what you are capable of performing from start to end completely on your own. List them."
LIMITS_PROMPT = "What can you NOT do?"
DECISION_PROMPT = (
    "Review the current Founder Experience and recommend the single highest-impact improvement "
    "to make AI Software Factory feel like a billion-dollar autonomous software company. "
    "Prepare a decision-ready mission for me to approve."
)
FALSE_POSITIVES = (
    "What can you do from start to end?",
    "Explain how to continue a mission.",
    "What workflows can you run?",
    "List what you can execute on your own.",
)


def _authorized(_: dict) -> dict:
    return {"authorized": True, "email": "founder@example.com"}


def main() -> None:
    decomposer = RequestDecomposer()
    capability_prompts = (CAPABILITY_PROMPT, LIMITS_PROMPT, FALSE_POSITIVES[0], FALSE_POSITIVES[2], FALSE_POSITIVES[3])
    for prompt in capability_prompts:
        assert decomposer.decompose(prompt)["intent_type"] == "informational_capability_query"
        assert ExecutionFirstPolicy.is_execution_instruction(prompt) is False
    assert decomposer.decompose(FALSE_POSITIVES[1])["intent_type"] != "informational_capability_query"
    assert ExecutionFirstPolicy.is_execution_instruction(FALSE_POSITIVES[1]) is False

    with patch("app.platform.operating_console.service.require_founder", _authorized), patch(
        "app.platform.board_room.executive_reasoning_engine.ContextRetriever.retrieve",
        side_effect=AssertionError("informational queries must bypass continuity retrieval"),
    ):
        result = board_room_chat({"token": "founder", "message": CAPABILITY_PROMPT})
    response = result["board_room_response"]
    assert result["presentation_contract"] == "founder-chat-v1"
    assert "- " in response and "My limits" in response
    for forbidden in ("MISSION-", "preserved blocker", "/100", "Jarvis must", "Execution-first routing"):
        assert forbidden not in response
    assert result["governance"]["execution_allowed"] is False
    assert "executive_reasoning" not in result and "technical_details" not in json.dumps(result)

    with patch("app.platform.operating_console.service.require_founder", _authorized), patch(
        "app.platform.board_room.executive_reasoning_engine.ContextRetriever.retrieve",
        side_effect=AssertionError("capability-limit queries must bypass continuity retrieval"),
    ):
        limits = board_room_chat({"token": "founder", "message": LIMITS_PROMPT})
    limits_response = limits["board_room_response"]
    assert "I cannot act outside" in limits_response
    assert "cannot approve my own" in limits_response
    assert limits["governance"]["execution_allowed"] is False
    assert "executive_reasoning" not in limits and "technical_details" not in json.dumps(limits)

    active_context = {
        "executive_continuity": {
            "mission_id": "MISSION-ACTIVE",
            "workflow_run_id": "MISSION-RUN-ACTIVE",
            "lifecycle_context": "mission_continuation",
        },
        "sources": {"mission_history": {"missions": [{
            "mission_id": "MISSION-ACTIVE",
            "workflow_run_id": "MISSION-RUN-ACTIVE",
            "status": "approved",
            "stage": "change_set_ready",
        }]}},
    }
    assert ExecutionFirstPolicy.should_execute("Continue the current mission.", active_context, {}) is True
    stale_context = {
        **active_context,
        "executive_continuity": {**active_context["executive_continuity"], "workflow_run_id": None},
    }
    assert ExecutionFirstPolicy.should_execute("Continue the current mission.", stale_context, {}) is False

    with patch("app.platform.operating_console.service.require_founder", _authorized), patch(
        "app.platform.operating_console.service.invoke_ai",
        return_value={"status": "completed", "output_text": "I recommend one focused founder-experience mission with governed approval controls."},
    ):
        decision = board_room_chat({"token": "founder", "message": DECISION_PROMPT})
    metadata = decision["action_metadata"]
    assert decision["presentation_contract"] == "founder-chat-v1"
    assert "executive_reasoning" not in decision and "technical_details" not in json.dumps(decision)
    assert [item["label"] for item in metadata["action_buttons"]] == ["Approve Mission", "Edit Scope", "Reject"]
    assert metadata["effort_band"] in {"Tiny", "Small", "Medium", "Large", "Epic"}
    assert metadata["estimated_effort"]

    rejection_actions = build_decision_ready_mission_actions(DECISION_PROMPT)
    rejection = next(item for item in rejection_actions["action_buttons"] if item["label"] == "Reject")
    with patch("app.platform.operating_console.action_service.require_founder", _authorized), patch(
        "app.platform.operating_console.action_service._load_state", return_value=None
    ), patch("app.platform.operating_console.action_service._persist_state", side_effect=AssertionError("rejection must not create a workflow record")), patch(
        "app.platform.operating_console.action_service.record_operational_evidence",
        return_value={"evidence_id": "EVIDENCE-REJECTED"},
    ) as rejection_evidence, patch(
        "app.platform.founder_approval.service._write_artifacts",
        side_effect=AssertionError("rejection must not mutate the repository"),
    ):
        rejected = dispatch_board_room_action({"token": "founder", **rejection["payload"]})
    assert rejected["status"] == "rejected"
    assert rejected["mission_id"] is None and rejected["workflow_run_id"] is None
    assert rejected["decision_evidence"]["evidence_id"] == "EVIDENCE-REJECTED"
    rejection_evidence.assert_called_once()

    with patch.dict("os.environ", {"GIT_COMMIT_SHA": "abcdef123456", "K_REVISION": "service-00042-abc"}, clear=False):
        html = render_dashboard()
    # The "Agents" section became "Organisation" (AFOS-017A, #456); the agent roster lives there now.
    assert 'data-section="organisation">Organisation' in html
    assert '<section id="organisation"' in html
    assert html.index('data-section="organisation"') < html.index('data-section="settings"')
    assert "abcdef12" in html and "00042-abc" in html
    assert "decision:decision||null" in html
    assert "Effort:" in html and "window.editRecommendedScope=function(payload)" in html
    assert "missionLifecycleCard" in html
    for label in ("Recommendation", "Mission", "Planning", "Execution", "Verification", "Complete"):
        assert label in html
    print("AFOS-008 Jarvis routing and production UI regression checks passed")


if __name__ == "__main__":
    main()
