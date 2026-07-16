from __future__ import annotations

from unittest.mock import patch

import app.platform.execution.service as execution_service
from app.platform.agents.specialists import architect_agent_handler
from app.platform.capability_intelligence.service import discover_relevant_capabilities
from app.platform.execution.orchestrator import launch_approved_mission_workflow
from app.platform.journey_inspection.service import inspect_mission_journey
from app.platform.planning.service import generate_engineering_plan
from app.platform.repository_intelligence.service import inspect_repository_evidence


MISSION_ID = "MISSION-WORKFLOW-01"


def _authorized(_: dict) -> dict:
    return {"authorized": True, "role": "founder"}


def _approval(mission_id: str = MISSION_ID) -> dict:
    return {
        "status": "approved",
        "mission_id": mission_id,
        "approval": {"decision": "approved", "mission_id": mission_id, "approval_id": "APPR-1"},
    }


def _run(approval: dict | None = None, progress_observer=None) -> dict:
    return launch_approved_mission_workflow({
        "token": "founder-token",
        "approval": approval or _approval(),
        "founder_request": "Implement a small UI polish mission.",
        "title": "Small UI polish",
        "progress_observer": progress_observer,
    })


def main() -> None:
    execution_service._ACTIVE_MISSION = None
    missing = _run({})
    rejected = _run({"approval": {"decision": "rejected", "mission_id": MISSION_ID}})
    wrong_mission = launch_approved_mission_workflow({"token": "founder-token", "mission_id": "MISSION-OTHER", "approval": _approval(), "founder_request": "UI polish"})
    assert missing["workflow_status"] == "blocked"
    assert rejected["workflow_status"] == "blocked"
    assert wrong_mission["workflow_status"] == "blocked"
    assert "different mission" in wrong_mission["blocked_reason"]
    assert execution_service._ACTIVE_MISSION is None

    call_order = []
    progress = []
    def observe(**event):
        progress.append((event["stage"], event["status"]))
    def tracked_plan(*args, **kwargs):
        call_order.append("planning")
        return generate_engineering_plan(*args, **kwargs)
    def tracked_capabilities(*args, **kwargs):
        call_order.append("capability_intelligence")
        return discover_relevant_capabilities(*args, **kwargs)
    def tracked_repository(*args, **kwargs):
        call_order.append("repository_evidence")
        return inspect_repository_evidence(*args, **kwargs)
    def tracked_architect(*args, **kwargs):
        call_order.append("architecture_agent")
        return architect_agent_handler(*args, **kwargs)

    with patch("app.platform.execution.service.require_founder", _authorized), patch("app.platform.planning.service.require_founder", _authorized), patch("app.platform.engineering_manager.service.require_founder", _authorized), patch("app.platform.execution.orchestrator.generate_engineering_plan", side_effect=tracked_plan), patch("app.platform.execution.orchestrator.discover_relevant_capabilities", side_effect=tracked_capabilities), patch("app.platform.execution.orchestrator.inspect_repository_evidence", side_effect=tracked_repository), patch("app.platform.execution.orchestrator.architect_agent_handler", side_effect=tracked_architect) as architect:
        completed = _run(progress_observer=observe)
        first_plan_id = completed["planning_result"]["plan"]["plan_id"]
        first_breakdown_id = completed["engineering_handoff"]["breakdown_id"]
        repeated = _run()

    assert completed["mission_id"] == MISSION_ID
    assert completed["workflow_status"] == "engineering-handoff-prepared"
    assert completed["mission_launch_status"] == "launched"
    assert completed["planning_result"]["plan"]["mission_id"] == MISSION_ID
    assert completed["engineering_handoff"]["mission_id"] == MISSION_ID
    assert completed["engineering_handoff"]["founder_request"] == completed["planning_result"]["plan"]["founder_request"]
    assert completed["current_stage"] == "engineering_handoff_prepared"
    assert completed["architecture_review"]["agent_id"] == "architect_agent"
    assert completed["architecture_review_status"] == "completed"
    assert completed["architecture_review"]["architecture_plan"]["requested_repository_evidence"]
    assert completed["architecture_review"]["architecture_decision"]["status"] == "validated"
    assert completed["architecture_review"]["architecture_decision"]["capability_context_id"].startswith("CAPCTX-")
    assert completed["engineering_handoff"]["architecture_decision"]["status"] == "validated"
    assert completed["engineering_handoff"]["capability_context_id"].startswith("CAPCTX-")
    assert call_order.index("planning") < call_order.index("capability_intelligence") < call_order.index("repository_evidence") < call_order.index("architecture_agent")
    expected_progress = [
        ("planning", "running"), ("planning", "completed"),
        ("capability_intelligence", "running"), ("capability_intelligence", "completed"),
        ("repository_intelligence", "running"), ("repository_intelligence", "completed"),
        ("architecture_agent", "running"), ("architecture_validation", "running"),
        ("architecture_validation", "completed"), ("architecture_agent", "completed"),
        ("engineering_manager", "running"), ("engineering_manager", "completed"),
    ]
    assert progress == expected_progress, progress
    assert completed["next_required_action"] == "Authorize engineering execution."
    assert all(completed["governance"][key] is False for key in ("repository_mutation", "branch_creation", "pull_request_creation", "merge", "deployment"))
    assert repeated["mission_launch_status"] == "reused"
    assert repeated["planning_status"] == "reused"
    assert repeated["engineering_handoff_status"] == "reused"
    assert repeated["architecture_review_status"] == "reused"
    assert repeated["planning_result"]["plan"]["plan_id"] == first_plan_id
    assert repeated["engineering_handoff"]["breakdown_id"] == first_breakdown_id
    assert architect.call_count == 1

    journey = inspect_mission_journey(MISSION_ID)
    planning_stage = next(item for item in journey["stages"] if item["stage_id"] == "planning")
    engineering_stage = next(item for item in journey["stages"] if item["stage_id"] == "engineering_execution")
    assert planning_stage["status"] == "verified"
    assert engineering_stage["status"] == "ready"
    assert "handoff is prepared" in engineering_stage["explanation"]

    execution_service._ACTIVE_MISSION = None
    failed_plan = {"status": "planning-failed", "authenticated": True, "mission_id": MISSION_ID, "error": "test failure"}
    with patch("app.platform.execution.service.require_founder", _authorized), patch("app.platform.execution.orchestrator.generate_engineering_plan", return_value=failed_plan), patch("app.platform.execution.orchestrator.create_engineering_breakdown", side_effect=AssertionError("engineering handoff must not run")):
        failed = _run()
    assert failed["workflow_status"] == "blocked"
    assert failed["mission_id"] == MISSION_ID
    assert failed["current_stage"] == "planning"
    assert failed["planning_status"] == "failed"
    assert failed["engineering_handoff_status"] == "not-started"
    assert failed["failure_evidence"] == failed_plan
    print("founder approval to mission launch workflow ok")


if __name__ == "__main__":
    main()
