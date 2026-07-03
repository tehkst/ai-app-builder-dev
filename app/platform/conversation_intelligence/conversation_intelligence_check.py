from __future__ import annotations

from app.platform.conversation_intelligence.service import analyze_conversation, build_conversation_intelligence_summary


def main() -> None:
    summary = build_conversation_intelligence_summary()
    assert summary["milestone"] == "CI-02"
    assert summary["status"] == "conversation-intelligence-v2-ready"

    roadmap_prompt = """
    Please perform a live architectural review of Mission Control using the current production system and repository.
    Produce a prioritized roadmap of the next 10 engineering missions.
    Do not implement anything yet. Only produce the executive engineering roadmap for Founder approval.
    """
    roadmap = analyze_conversation({"message": roadmap_prompt})["conversation_intelligence"]
    assert roadmap["mode"] == "Architecture Review"
    assert roadmap["workflow_type"] == "roadmap"
    assert roadmap["mission_required"] is True
    assert roadmap["coding_required"] is False
    assert roadmap["deployment_required"] is False
    assert roadmap["roadmap_proposal"]["implementation_allowed"] is False
    assert len(roadmap["roadmap_proposal"]["missions"]) == 10

    implementation = analyze_conversation({"message": "Implement CI-02 now using a small reviewable PR."})["conversation_intelligence"]
    assert implementation["mode"] == "Implementation Mission"
    assert implementation["workflow_type"] == "implementation"
    assert implementation["coding_required"] is True

    deployment = analyze_conversation({"message": "Deploy the latest Cloud Run revision to production traffic."})["conversation_intelligence"]
    assert deployment["mode"] == "Deployment"
    assert deployment["workflow_type"] == "deployment"
    assert deployment["deployment_required"] is True

    auth = analyze_conversation({"message": "Fix login session token handling."})["conversation_intelligence"]
    assert auth["mode"] == "Authentication / Security"
    assert auth["workflow_type"] == "security_review"

    general = analyze_conversation({"message": "Explain how this works."})["conversation_intelligence"]
    assert general["mode"] == "Knowledge / Clarification"
    assert general["mission_required"] is False

    print("CONVERSATION INTELLIGENCE CHECK PASSED")


if __name__ == "__main__":
    main()
