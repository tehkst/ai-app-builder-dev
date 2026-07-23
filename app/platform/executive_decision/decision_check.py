from __future__ import annotations

from app.platform.executive_decision.service import build_executive_decision_summary, decide_next_action


def main() -> None:
    summary = build_executive_decision_summary()
    assert summary["milestone"] == "AFOS-002"
    assert summary["status"] == "guided-executive-decision-ready"
    assert summary["workflow_authority"] == "existing_founder_workflow_engine"

    roadmap = decide_next_action(
        {
            "message": "Review Mission Control architecture and recommend the next engineering mission.",
            "conversation_intelligence": {"mode_key": "architecture_review", "workflow_type": "roadmap", "mission_required": True},
        }
    )
    assert roadmap["primary_action"]["key"] == "generate_architecture_roadmap"
    assert roadmap["primary_action"]["label"] == "Generate Architecture Roadmap"
    assert roadmap["primary_action"]["requires_workflow"] is True

    discussion = decide_next_action(
        {
            "message": "Can you explain how this works?",
            "conversation_intelligence": {"mode_key": "knowledge", "workflow_type": "knowledge_note", "mission_required": False},
        }
    )
    assert discussion["primary_action"]["key"] == "continue_discussion"
    assert discussion["primary_action"]["requires_workflow"] is False

    implementation = decide_next_action(
        {
            "message": "Implement BR-UX-01 now.",
            "conversation_intelligence": {"mode_key": "implementation", "workflow_type": "implementation", "mission_required": True},
        }
    )
    assert implementation["primary_action"]["key"] == "create_engineering_proposal"

    incident = decide_next_action(
        {
            "message": "Login is broken in production.",
            "conversation_intelligence": {"mode_key": "security_auth", "workflow_type": "security_review", "mission_required": True},
        }
    )
    assert incident["primary_action"]["key"] == "create_incident"

    deployment = decide_next_action(
        {
            "message": "Deploy the newest Cloud Run revision.",
            "conversation_intelligence": {"mode_key": "deployment", "workflow_type": "deployment", "mission_required": True},
        }
    )
    assert deployment["primary_action"]["key"] == "create_deployment_review"

    print("EXECUTIVE DECISION CHECK PASSED")


if __name__ == "__main__":
    main()
