from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import app.platform.execution.service as execution_service
from app.platform.execution.orchestrator import execute_authorized_engineering_workflow, launch_approved_mission_workflow
from app.platform.github_execution.approved_executor import APPROVAL_PHRASE, _pr_body_with_mission_marker, execute_approved_github_execution
from app.platform.journey_inspection.service import inspect_mission_journey


MISSION_ID = "MISSION-WORKFLOW-02"
FILE_CHANGES = [{"path": "app/example.py", "content": "VALUE = 1\n"}]


def _authorized(_: dict) -> dict:
    return {"authorized": True, "role": "founder"}


def _prepare_handoff() -> None:
    execution_service._ACTIVE_MISSION = None
    approval = {"mission_id": MISSION_ID, "approval": {"decision": "approved", "mission_id": MISSION_ID}}
    with patch("app.platform.execution.service.require_founder", _authorized), patch("app.platform.planning.service.require_founder", _authorized), patch("app.platform.engineering_manager.service.require_founder", _authorized):
        result = launch_approved_mission_workflow({"token": "founder", "approval": approval, "founder_request": "Implement a small UI polish mission."})
    assert result["workflow_status"] == "engineering-handoff-prepared"


def _payload(**overrides: object) -> dict:
    payload = {
        "token": "founder",
        "mission_id": MISSION_ID,
        "authorization_status": "approved",
        "authorization_mission_id": MISSION_ID,
        "authorization_action": "github_execution",
        "live_execution": True,
        "approval_phrase": APPROVAL_PHRASE,
        "file_changes": FILE_CHANGES,
    }
    payload.update(overrides)
    return payload


def _execution_result() -> dict:
    return {
        "status": "pull-request-created",
        "mission_id": MISSION_ID,
        "branch_name": f"mission/{MISSION_ID}",
        "commit": "commit123",
        "files_changed": ["app/example.py"],
        "pull_request_number": 456,
        "pull_request_url": "https://github.com/tehkst/ai-app-builder-dev/pull/456",
        "merge": False,
        "deployment": False,
    }


def _lifecycle(mission_id: str | None = MISSION_ID, resolution: str = "resolved") -> dict:
    return {"status": "pr-status-ready", "state": "open", "pr_number": 456, "mission_id": mission_id, "mission_resolution_status": resolution, "merged": False, "merge": False, "deployment": False}


def main() -> None:
    _prepare_handoff()
    executor = Mock(side_effect=AssertionError("repository execution must not run"))
    expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    blocked_payloads = [
        _payload(approval_phrase=""),
        _payload(authorization_status="rejected"),
        _payload(authorization_expires_at=expired),
        _payload(authorization_mission_id="MISSION-OTHER"),
        _payload(authorization_action="merge"),
    ]
    with patch("app.platform.execution.orchestrator.execute_approved_github_execution", executor):
        blocked = [execute_authorized_engineering_workflow(item) for item in blocked_payloads]
    assert all(item["workflow_status"] == "blocked" for item in blocked)
    assert all(item["repository_change_status"] == "not-started" for item in blocked)
    assert executor.call_count == 0

    with patch("app.platform.execution.orchestrator.validate_code_proposal", return_value={"status": "validation-failed", "checks": [{"status": "fail"}]}), patch("app.platform.execution.orchestrator.execute_approved_github_execution", executor):
        validation_failed = execute_authorized_engineering_workflow(_payload())
    assert validation_failed["current_stage"] == "validation"
    assert validation_failed["pr_status"] == "not-created"
    assert executor.call_count == 0

    execution_service._ACTIVE_MISSION.pop("repository_validation", None)
    github_execution = Mock(return_value=_execution_result())
    with patch("app.platform.execution.orchestrator.validate_code_proposal", return_value={"status": "validated", "checks": [{"status": "pass"}]}), patch("app.platform.execution.orchestrator.execute_approved_github_execution", github_execution), patch("app.platform.execution.orchestrator.get_github_pr_status", return_value=_lifecycle()):
        successful = execute_authorized_engineering_workflow(_payload())
        repeated = execute_authorized_engineering_workflow(_payload())
    assert successful["workflow_status"] == "pull-request-created-and-observed"
    assert successful["mission_id"] == MISSION_ID
    assert successful["branch"] == f"mission/{MISSION_ID}"
    assert successful["commit_sha"] == "commit123"
    assert successful["pr_number"] == 456
    assert successful["current_stage"] == "pull_request_created_or_observed"
    assert successful["governance"]["merge"] is False and successful["governance"]["deployment"] is False
    assert repeated["engineering_execution_status"] == "reused"
    assert github_execution.call_count == 1
    execution_payload = github_execution.call_args.args[0]
    assert execution_payload["mission_id"] == MISSION_ID
    assert execution_payload["approved_plan"]["plan"]["mission_id"] == MISSION_ID
    assert execution_payload["engineering_handoff"]["mission_id"] == MISSION_ID
    assert _pr_body_with_mission_marker("Approved engineering execution.", MISSION_ID).endswith(f"Mission-ID: {MISSION_ID}")

    executor_result = {"commit": "commit123", "files_changed": ["app/example.py"], "pull_request_number": 456, "pull_request_url": "https://github.com/tehkst/ai-app-builder-dev/pull/456"}
    with patch.dict("os.environ", {"GITHUB_TOKEN": "secret"}), patch("app.platform.github_execution.approved_executor.require_founder", _authorized), patch("app.platform.github_execution.approved_executor._perform_execution", return_value=executor_result):
        approved_executor = execute_approved_github_execution({"token": "founder", "mission_id": MISSION_ID, "title": "UI polish", "branch_name": f"mission/{MISSION_ID}", "commit_message": "Implement mission", "pr_title": "UI polish", "file_changes": FILE_CHANGES, "live_execution": True, "approval_phrase": APPROVAL_PHRASE})
    assert approved_executor["pull_request_number"] == 456
    assert approved_executor["mission_id"] == MISSION_ID
    assert approved_executor["merge"] is False and approved_executor["deployment"] is False

    journey = inspect_mission_journey(MISSION_ID)
    for stage_id in ("engineering_execution", "code_changes", "pull_request"):
        assert next(item for item in journey["stages"] if item["stage_id"] == stage_id)["status"] == "verified"

    execution_service._ACTIVE_MISSION["pr_lifecycle_result"] = {}
    with patch("app.platform.execution.orchestrator.get_github_pr_status", return_value=_lifecycle(None, "ambiguous")):
        conflict = execute_authorized_engineering_workflow(_payload())
    assert conflict["workflow_status"] == "blocked"
    assert conflict["current_stage"] == "pr_lifecycle"

    execution_service._ACTIVE_MISSION.pop("repository_execution", None)
    execution_service._ACTIVE_MISSION.pop("pr_lifecycle_result", None)
    partial = {"status": "github-execution-failed", "mission_id": MISSION_ID, "branch_name": f"mission/{MISSION_ID}", "commit": "commit123", "push_status": "completed", "failed_stage": "pull_request_creation", "error": "PR creation failed"}
    with patch("app.platform.execution.orchestrator.execute_approved_github_execution", return_value=partial):
        failed = execute_authorized_engineering_workflow(_payload())
    assert failed["workflow_status"] == "blocked"
    assert failed["branch"] == f"mission/{MISSION_ID}"
    assert failed["commit_sha"] == "commit123"
    assert failed["current_stage"] == "pull_request_creation"
    assert failed["repository_change_status"] == "completed"
    assert failed["push_status"] == "completed"
    print("engineering handoff to pull request workflow ok")


if __name__ == "__main__":
    main()
