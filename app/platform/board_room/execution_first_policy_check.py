from __future__ import annotations

import json

from app.platform.board_room.execution_first_policy import ExecutionFirstPolicy


def run_check() -> dict[str, object]:
    context = {
        "executive_continuity": {
            "has_context": True,
            "mission_id": "MISSION-44BE9D1DAF0E",
            "workflow_run_id": "MISSION-RUN-D1A8377244497406",
            "lifecycle_context": "mission_continuation",
            "blocking_reason": None,
        },
        "sources": {
            "mission_history": {
                "missions": [
                    {
                        "mission_id": "MISSION-44BE9D1DAF0E",
                        "stage": "change_set_ready",
                        "status": "approved",
                    }
                ]
            }
        },
    }

    assert ExecutionFirstPolicy.should_execute("Proceed with AFOS-001", context, {}) is True
    assert ExecutionFirstPolicy.should_execute("Implement the approved mission now", context, {}) is True
    assert ExecutionFirstPolicy.should_execute("What do you recommend next?", context, {}) is False

    handoff = ExecutionFirstPolicy.handoff("Proceed", context, {})
    reasoning = handoff.get("reasoning") or {}
    execution = reasoning.get("execution_handoff") or {}
    response = str(handoff.get("founder_response") or "")

    assert reasoning.get("intent") == "execute_approved_mission"
    assert reasoning.get("presentation_mode") == "execution_handoff"
    assert execution.get("execution_authority") == "existing_mission_pipeline"
    assert execution.get("governance_boundary") is False
    assert "recommend" not in response.lower()
    assert "EXECUTION REQUIRED" in response

    blocked_context = {
        **context,
        "executive_continuity": {
            **context["executive_continuity"],
            "blocking_reason": "Waiting for engineering execution approval",
        },
    }
    blocked = ExecutionFirstPolicy.handoff("Proceed", blocked_context, {})
    blocked_execution = (blocked.get("reasoning") or {}).get("execution_handoff") or {}
    assert blocked_execution.get("governance_boundary") is True
    assert "PAUSED AT GOVERNANCE BOUNDARY" in str(blocked.get("founder_response") or "")

    return {
        "milestone": "CORE-001",
        "status": "passed",
        "routing": "execution-before-recommendation",
        "execution_authority": "existing_mission_pipeline",
        "duplicate_runner_created": False,
    }


if __name__ == "__main__":
    print(json.dumps(run_check(), indent=2, sort_keys=True))
