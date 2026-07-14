from __future__ import annotations

from unittest.mock import patch

import app.platform.execution.service as execution_service
from app.platform.agents.specialists import architect_agent_handler
from app.platform.execution.orchestrator import launch_approved_mission_workflow
from app.platform.journey_inspection.service import inspect_mission_journey


MISSION_ID = "MISSION-WORKFLOW-01"


def _authorized(_: dict) -> dict:
    return {"authorized": True, "role": "founder"}


def _approval(mission_id: str = MISSION_ID) -> dict:
    return {
        "status": "approved",
        "mission_id": mission_id,
        "approval": {"decision": "approved", "mission_id": mission_id, "approval_id": "APPR-1"},
    }


def _run(approval: dict | None = None) -> dict:
    return launch_approved_mission_workflow({
        "token": "founder-token",
        "approval": approval or _approval(),
        "founder_request": "Implement a small UI polish mission.",
        "title": "Small UI polish",
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

    with patch("app.platform.execution.service.require_founder", _authorized), patch("app.platform.planning.service.require_founder", _authorized), patch("app.platform.engineering_manager.service.require_founder", _authorized), patch("app.platform.execution.orchestrator.architect_agent_handler", wraps=architect_agent_handler) as architect:
        completed = _run()
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
