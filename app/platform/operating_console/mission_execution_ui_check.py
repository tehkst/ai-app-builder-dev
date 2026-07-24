from __future__ import annotations

from unittest.mock import patch

from app.platform.operating_console import action_service
from app.platform.operating_console import mission_run_service as runtime
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformAgentTask, PlatformWorkflowRun
from app.platform.ui.dashboard_browser_script import render_dashboard_browser_script
from app.platform.ui.executive_presenter_script import render_executive_presenter_script
from app.platform.ui.founder_dashboard_stable import render_stable_founder_dashboard


REQUEST = "Create a file named deployment-smoke-390.txt containing PR 390 production smoke test."


def _authorized(_: dict) -> dict:
    return {"authorized": True, "role": "founder", "email": "founder@example.com"}


def main() -> None:
    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        db.query(PlatformAgentTask).filter(PlatformAgentTask.task_type == runtime.TASK_TYPE).delete(synchronize_session=False)
        db.query(PlatformWorkflowRun).filter(PlatformWorkflowRun.workflow_name == "Durable Board Room Mission Run").delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

    no_context = runtime.build_mission_execution_summary()
    assert no_context["active_mission"] is None
    assert no_context["message"] == "Select or create a Board Room mission before creating an execution mission."

    actions = action_service.build_pending_mission_actions(REQUEST, provider="openai", model="gpt-5.5")
    launch = next(button for button in actions["action_buttons"] if button["label"] == "Approve Mission")
    context = launch["payload"]["action_context"]
    readiness = {"durable_runtime_available": True, "connection_verified": True}
    with (
        patch.object(action_service, "require_founder", _authorized),
        patch.object(action_service, "_load_state", return_value=None),
        patch.object(action_service, "_persist_state"),
        patch("app.platform.founder_approval.service._write_artifacts"),
        patch.object(runtime, "inspect_platform_persistence_readiness", return_value=readiness),
        patch.object(runtime, "verify_platform_persistence_connection", return_value=readiness),
        patch.object(runtime, "_activate_canonical_worker"),
    ):
        created = action_service.dispatch_board_room_action({"token": "founder-session", **launch["payload"]})
        repeated = action_service.dispatch_board_room_action({"token": "founder-session", **launch["payload"]})

    assert created["mission_id"] == context["mission_id"]
    assert created["founder_request"] == REQUEST
    assert "deployment-smoke-390.txt" in created["title"]
    assert created["originating_mission_id"] == context["mission_id"]
    assert created["original_mission_id"] == context["mission_id"]
    assert created["workflow_run_id"] and created["action_context_id"]
    assert created["context_signature"] == launch["payload"]["context_signature"]
    assert created["approval"]["status"] == "approved"
    assert created["runtime_classification"] == "durable_platform_workflow"
    assert created["durable_runtime_created"] is True
    assert created["provider"] == "openai" and created["model"] == "gpt-5.5"
    assert repeated["workflow_run_id"] == created["workflow_run_id"] and repeated["reused"] is True
    assert "founder-session" not in str(runtime.load_mission_run(created["workflow_run_id"]))

    refreshed = runtime.build_mission_execution_summary()
    mission = refreshed["active_mission"]
    assert mission["mission_id"] == created["mission_id"]
    assert mission["workflow_run_id"] == created["workflow_run_id"]
    assert mission["founder_request"] == REQUEST
    assert mission["current_stage"] == created["progress"]["current_stage"]
    assert mission["progress_percentage"] == runtime._delivery_progress(
        runtime.load_mission_run(created["workflow_run_id"])["delivery_contract"]
    )
    assert runtime._delivery_progress(None) is None
    assert mission["task_status"]["count"] == 1
    runtime._RUN_CREDENTIALS.clear()
    durable_after_process_reset = runtime.build_mission_execution_summary()["active_mission"]
    assert durable_after_process_reset["mission_id"] == created["mission_id"]
    assert durable_after_process_reset["workflow_run_id"] == created["workflow_run_id"]

    with patch.object(runtime, "require_founder", _authorized), patch.object(runtime, "_activate_canonical_worker"):
        continued = runtime.continue_mission_run({"token": "founder-session", "mission_id": mission["mission_id"], "workflow_run_id": mission["workflow_run_id"]})
    assert continued["mission_id"] == mission["mission_id"]
    assert continued["workflow_run_id"] == mission["workflow_run_id"]

    db = PlatformSessionLocal()
    try:
        runs = db.query(PlatformWorkflowRun).filter(PlatformWorkflowRun.workflow_name == "Durable Board Room Mission Run").all()
        tasks = db.query(PlatformAgentTask).filter(PlatformAgentTask.parent_task_id == created["workflow_run_id"]).all()
        assert len(runs) == 1 and len(tasks) == 1
    finally:
        db.close()

    state = runtime.load_mission_run(created["workflow_run_id"])
    runtime._progress_observer(state)(stage="planning", status="running", summary="Planning started.")
    advanced = runtime.build_mission_execution_summary()["active_mission"]
    assert advanced["mission_id"] == created["mission_id"]
    assert advanced["workflow_run_id"] == created["workflow_run_id"]
    assert advanced["current_stage"] == "planning_running"

    supported_stages = [
        "accepted", "planning_running", "capability_intelligence_running",
        "repository_intelligence_running", "architecture_agent_running",
        "architecture_validation_running", "engineering_manager_running",
        "change_set_generation_running", "change_set_validation_running",
        "change_set_repair_running",
    ]
    for stage in supported_stages:
        candidate = {**state, "status": stage, "current_stage": stage, "error": None}
        with (
            patch.object(runtime, "require_founder", _authorized),
            patch.object(runtime, "load_mission_run", return_value=candidate),
            patch.object(runtime, "_activate_canonical_worker"),
        ):
            result = runtime.continue_mission_run({
                "token": "founder-session", "mission_id": candidate["mission_id"],
                "workflow_run_id": candidate["workflow_run_id"],
            })
        assert result["ok"] is True and result["advance_allowed"] is True, (stage, result)
        assert result["mission_id"] == candidate["mission_id"]
        assert result["workflow_run_id"] == candidate["workflow_run_id"]

    ready_state = runtime.load_mission_run(created["workflow_run_id"])
    runtime._advance(ready_state, "change_set_ready", "Change set ready for founder review.")
    ready_summary = runtime.build_mission_execution_summary()["active_mission"]
    assert ready_summary["current_stage"] == "change_set_ready"
    assert ready_summary["advance_allowed"] is False
    assert ready_summary["next_governed_action"]["action_type"] == "show_section"
    assert ready_summary["next_governed_action"]["target"] == "executions"
    assert "GitHub Execution" in ready_summary["next_governed_action"]["label"]
    with patch.object(runtime, "require_founder", _authorized):
        invalid = runtime.continue_mission_run({
            "token": "founder-session", "mission_id": ready_summary["mission_id"],
            "workflow_run_id": ready_summary["workflow_run_id"],
        })
    assert invalid["ok"] is False and invalid["error"]["classification"] == "invalid_stage_transition"
    assert invalid["mission_id"] == ready_summary["mission_id"]
    assert invalid["workflow_run_id"] == ready_summary["workflow_run_id"]
    assert "cannot advance" in invalid["message"]

    for stage in ("blocked", "failed"):
        terminal = {**ready_state, "status": stage, "current_stage": stage, "error": {"classification": "validation_failure"}}
        assert runtime._advance_allowed(terminal) is False
        assert runtime._next_governed_action(terminal)["action_type"] == "none"
    authorization_block = {
        **ready_state, "status": "blocked", "current_stage": "blocked",
        "error": {"classification": "authorization_resume_required"},
    }
    assert runtime._advance_allowed(authorization_block) is True
    assert runtime._next_governed_action(authorization_block)["action_type"] == "advance"

    script = render_dashboard_browser_script()
    assert "/mission-control/execution/create" not in script
    assert "/mission-control/execution/from-board-room" not in script
    assert "Select or create a Board Room mission before creating an execution mission." in script
    assert "window.currentDurableMissionAction" in script
    assert "localStorage.setItem('currentDurableMission" not in script
    assert "workflowPipelineState" in script and "task_status" in script
    assert "data.ok===false" in script and "executionFeedback('Execution continuation failed:" in script
    assert "sectionFromLocation()" in script and "window.location.hash" in script
    assert "window.history.replaceState" in script and "hashchange" in script
    assert "mission_control_active_section" not in script
    assert "localStorage.setItem('currentDurableMission" not in script
    assert "sessionStorage" not in script
    presenter = render_executive_presenter_script()
    assert "Workflow Run ID" in presenter and "mission.workflow_run_id" in presenter
    dashboard = render_stable_founder_dashboard()
    assert 'id="executionMissionFeedback"' in dashboard
    assert 'id="advanceExecutionMissionBtn" disabled' in dashboard
    print("durable mission execution UI lifecycle ok")


if __name__ == "__main__":
    main()
