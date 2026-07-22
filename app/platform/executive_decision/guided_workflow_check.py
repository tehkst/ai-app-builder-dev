from __future__ import annotations

import json

from app.platform.executive_decision.service import decide_next_action


def run_check() -> dict[str, object]:
    incident = decide_next_action({"message": "Production login is broken and users cannot access the app."})
    assert incident["primary_action"]["key"] == "create_incident"
    assert incident["guided_workflow"]["workflow_type"] == "incident"
    assert incident["guided_workflow"]["workflow_authority"] == "existing_founder_workflow_engine"

    roadmap = decide_next_action(
        {
            "message": "Review the architecture roadmap. Do not implement yet.",
            "conversation_intelligence": {
                "mode_key": "architecture_review",
                "workflow_type": "roadmap",
                "mission_required": True,
            },
        }
    )
    assert roadmap["primary_action"]["key"] == "generate_architecture_roadmap"
    assert roadmap["guided_workflow"]["workflow_type"] == "roadmap"
    assert roadmap["guided_workflow"]["approval_scope"] == "planning_only"
    assert roadmap["guided_workflow"]["implementation_authorized"] is False

    implementation = decide_next_action(
        {
            "message": "Implement the approved mission.",
            "conversation_intelligence": {
                "mode_key": "implementation",
                "workflow_type": "implementation",
                "mission_required": True,
            },
        }
    )
    assert implementation["primary_action"]["key"] == "create_engineering_proposal"
    assert implementation["guided_workflow"]["workflow_type"] == "mission"
    assert implementation["guided_workflow"]["approval_scope"] == "implementation"
    assert implementation["guided_workflow"]["founder_approval_required"] is True

    deployment = decide_next_action(
        {
            "message": "Deploy the approved release to production.",
            "conversation_intelligence": {
                "mode_key": "deployment",
                "workflow_type": "deployment",
                "mission_required": True,
            },
        }
    )
    assert deployment["primary_action"]["key"] == "create_deployment_review"
    assert deployment["guided_workflow"]["approval_scope"] == "production_deployment"
    assert deployment["guided_workflow"]["deployment_authorized"] is False

    discussion = decide_next_action(
        {
            "message": "Explain why this matters.",
            "conversation_intelligence": {
                "mode_key": "knowledge",
                "workflow_type": "knowledge_note",
                "mission_required": False,
            },
        }
    )
    assert discussion["primary_action"]["key"] == "continue_discussion"
    assert discussion["guided_workflow"]["enabled"] is False

    for decision in (incident, roadmap, implementation, deployment, discussion):
        governance = decision["governance"]
        assert governance["decision_engine_owns_workflow"] is False
        assert governance["duplicate_workflow_created"] is False
        assert governance["duplicate_approval_model_created"] is False

    return {
        "milestone": "AFOS-002",
        "status": "passed",
        "decision_authority": "existing_executive_decision_center",
        "workflow_authority": "existing_founder_workflow_engine",
        "duplicate_engine_created": False,
    }


if __name__ == "__main__":
    print(json.dumps(run_check(), indent=2, sort_keys=True))
