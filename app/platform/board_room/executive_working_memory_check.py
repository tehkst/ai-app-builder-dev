from __future__ import annotations

import json

from app.platform.board_room.executive_working_memory import ExecutiveWorkingMemory


def run_check() -> dict[str, object]:
    context = {
        "executive_continuity": {
            "mission_id": "MISSION-44BE9D1DAF0E",
            "workflow_run_id": "MISSION-RUN-D1A8377244497406",
            "blocking_reason": None,
        },
        "sources": {
            "mission_history": {
                "missions": [
                    {
                        "mission_id": "MISSION-44BE9D1DAF0E",
                        "workflow_run_id": "MISSION-RUN-D1A8377244497406",
                        "status": "Engineering",
                        "current_autonomous_stage": "engineering",
                        "next_action": "Open the implementation pull request.",
                        "blocking_reason": None,
                        "synthetic": False,
                    }
                ]
            }
        },
    }

    memory = ExecutiveWorkingMemory.build(context)
    mission = memory["mission"]

    assert memory["status"] == "executive-working-memory-ready"
    assert memory["execution_authority"] == "existing_mission_pipeline"
    assert memory["stores_state"] is False
    assert memory["creates_new_registry"] is False
    assert mission["mission_id"] == "MISSION-44BE9D1DAF0E"
    assert mission["current_stage"] == "engineering"
    assert mission["next_stage"] == "pr"
    assert mission["next_action"] == "Open the implementation pull request."
    assert mission["completed_stages"] == ["planning"]

    blocked_context = {
        **context,
        "sources": {
            "mission_history": {
                "missions": [
                    {
                        **context["sources"]["mission_history"]["missions"][0],
                        "blocking_reason": "Waiting for founder approval",
                    }
                ]
            }
        },
    }
    blocked = ExecutiveWorkingMemory.build(blocked_context)["mission"]
    assert blocked["next_stage"] == "engineering"

    complete_context = {
        **context,
        "sources": {
            "mission_history": {
                "missions": [
                    {
                        **context["sources"]["mission_history"]["missions"][0],
                        "status": "Complete",
                        "current_autonomous_stage": "complete",
                        "next_action": None,
                    }
                ]
            }
        },
    }
    complete = ExecutiveWorkingMemory.build(complete_context)
    assert complete["has_active_mission"] is False
    assert complete["mission"]["next_stage"] == "complete"

    return {
        "milestone": "CORE-002",
        "status": "passed",
        "working_memory": "existing-read-model-reconciliation",
        "mission_state_machine": True,
        "duplicate_registry_created": False,
    }


if __name__ == "__main__":
    print(json.dumps(run_check(), indent=2, sort_keys=True))
