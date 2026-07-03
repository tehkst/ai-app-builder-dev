from __future__ import annotations

from app.platform.founder_workflow.service import (
    advance_founder_workflow,
    build_founder_workflow_summary,
    create_founder_workflow,
    get_founder_workflow_status,
)


def main() -> None:
    summary = build_founder_workflow_summary()
    assert summary["milestone"] == "FWE-02"
    assert summary["status"] == "founder-workflow-engine-ready"
    assert summary["governance"]["direct_main_writes_allowed"] is False
    assert summary["governance"]["login_auth_untouched"] is True

    created = create_founder_workflow({"message": "Implement MC-001 Constitution integration"})
    workflow = created["workflow"]
    assert created["status"] == "workflow-card-created"
    assert workflow["current_stage"] == "founder_approval"
    assert workflow["allowed_actions"] == ["approve_mission", "edit_proposal", "reject"]

    blocked = advance_founder_workflow({"workflow_id": workflow["workflow_id"], "target_stage": "implementation_plan"})
    assert blocked["status"] == "blocked-awaiting-founder-approval"

    advanced = advance_founder_workflow(
        {
            "workflow_id": workflow["workflow_id"],
            "target_stage": "implementation_plan",
            "approval_status": "approved",
            "title": workflow["title"],
        }
    )
    assert advanced["status"] == "workflow-advanced"
    assert advanced["workflow"]["current_stage"] == "implementation_plan"

    status = get_founder_workflow_status({"workflow_id": workflow["workflow_id"], "stage": "pr_creation"})
    assert status["status"] == "workflow-status-ready"
    assert "GitHub Executor" in " ".join(status["workflow"]["blockers"])

    roadmap = create_founder_workflow(
        {
            "message": "Perform architecture review and produce a roadmap. Do not implement yet.",
            "workflow_type": "roadmap",
            "roadmap_proposal": {"missions": [{"mission_id": "MC-001"}]},
        }
    )["workflow"]
    assert roadmap["workflow_type"] == "roadmap"
    assert roadmap["allowed_actions"] == ["approve_roadmap", "edit_roadmap", "reject"]
    assert "planning only" in roadmap["approval_meaning"]
    assert roadmap["roadmap_mission_count"] == 1

    roadmap_advanced = advance_founder_workflow(
        {
            "workflow_id": roadmap["workflow_id"],
            "workflow_type": "roadmap",
            "target_stage": "mission_selection",
            "approval_status": "approved",
            "title": roadmap["title"],
        }
    )
    assert roadmap_advanced["status"] == "workflow-advanced"
    assert roadmap_advanced["workflow"]["current_stage"] == "mission_selection"

    print("FOUNDER WORKFLOW CHECK PASSED")


if __name__ == "__main__":
    main()
