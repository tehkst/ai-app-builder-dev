from __future__ import annotations

from unittest.mock import patch

from app.platform.agents import worker
from app.platform.agents.worker import execute_one_task
from app.platform.operating_console import mission_run_service as runtime
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformAgentTask, PlatformWorkflowRun
from app.platform.pipeline.mission_pipeline import MissionAggregator, _derive_status, _durable_auto_progress, _mission_progress, _recommendation


def main() -> None:
    create_platform_tables()
    mission_id = "MISSION-RUNTIME-RECONCILIATION"
    context = {
        "mission_id": mission_id,
        "action_context_id": "BOARD-ACTION-RUNTIME-RECONCILIATION",
        "founder_request": "Verify durable progress reconciliation.",
        "title": "Durable Progress Reconciliation",
    }
    db = PlatformSessionLocal()
    try:
        db.query(PlatformAgentTask).filter(PlatformAgentTask.parent_task_id.like("MISSION-RUN-%")).delete(synchronize_session=False)
        db.query(PlatformWorkflowRun).filter(PlatformWorkflowRun.workflow_name == "Durable Board Room Mission Run").delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

    readiness = {"durable_runtime_available": True, "connection_verified": True}
    with patch.object(runtime, "inspect_platform_persistence_readiness", return_value=readiness), patch.object(runtime, "verify_platform_persistence_connection", return_value=readiness), patch.object(runtime, "_activate_canonical_worker") as activate:
        accepted = runtime.accept_mission_run(context=context, signature="signature", approval={"status": "approved"}, token="founder-session")
        repeated = runtime.accept_mission_run(context=context, signature="signature", approval={"status": "approved"}, token="founder-session")
    assert accepted["workflow_run_id"] == repeated["workflow_run_id"] and repeated["reused"] is True
    assert accepted["mission_id"] == mission_id and accepted["action_context_id"] == context["action_context_id"]
    db = PlatformSessionLocal()
    try:
        tasks = db.query(PlatformAgentTask).filter(PlatformAgentTask.parent_task_id == accepted["workflow_run_id"]).all()
        assert len(tasks) == 1 and tasks[0].task_type == runtime.TASK_TYPE
    finally:
        db.close()
    assert activate.call_count == 2
    worker._ACTIVE_LOOPS.clear()
    with patch.object(worker.threading, "Thread") as thread:
        worker.ensure_agent_worker_running(task_type=runtime.TASK_TYPE)
        worker.ensure_agent_worker_running(task_type=runtime.TASK_TYPE)
    thread.assert_called_once()
    worker._ACTIVE_LOOPS.clear()

    runtime._RUN_CREDENTIALS.clear()
    first = execute_one_task(assigned_agent="reconciliation-worker", task_type=runtime.TASK_TYPE)
    assert first["status"] == "failed" and first["result"]["error"] == "authorization_resume_required"
    blocked = runtime.load_mission_run(accepted["workflow_run_id"])
    assert blocked["error"]["classification"] == "authorization_resume_required"

    db = PlatformSessionLocal()
    try:
        db.add_all([
            PlatformAgentTask(task_id="TASK-UNRELATED-AUTH", title="Unrelated", status="failed", priority="normal", risk_level="low", task_type=runtime.TASK_TYPE, requested_by="check", input_payload_json="{}", result_payload_json="{}", error_message="authorization_resume_required", parent_task_id="MISSION-RUN-OTHER", attempts=1, max_attempts=3),
            PlatformAgentTask(task_id="TASK-COMPLETED-AUTH", title="Completed", status="completed", priority="normal", risk_level="low", task_type=runtime.TASK_TYPE, requested_by="check", input_payload_json="{}", result_payload_json="{}", error_message=None, parent_task_id=accepted["workflow_run_id"], attempts=1, max_attempts=3),
            PlatformAgentTask(task_id="TASK-WRONG-FAILURE", title="Wrong failure", status="failed", priority="normal", risk_level="low", task_type=runtime.TASK_TYPE, requested_by="check", input_payload_json="{}", result_payload_json="{}", error_message="provider_non_json_response", parent_task_id=accepted["workflow_run_id"], attempts=1, max_attempts=3),
        ])
        db.commit()
    finally:
        db.close()

    with patch.object(runtime, "require_founder", return_value={"authorized": True}), patch.object(runtime, "_activate_canonical_worker") as resumed_worker:
        resumed = runtime.get_mission_run_status({"token": "restored-session", "workflow_run_id": accepted["workflow_run_id"]})
    assert resumed["progress"]["current_stage"] == "authorization_resumed" and resumed["progress"]["terminal"] is False
    resumed_worker.assert_called_once()
    db = PlatformSessionLocal()
    try:
        task = db.query(PlatformAgentTask).filter(PlatformAgentTask.parent_task_id == accepted["workflow_run_id"], PlatformAgentTask.status == "queued").one()
        assert task.status == "queued" and task.assigned_agent is None and task.result_payload_json == "{}"
        assert db.query(PlatformAgentTask).filter_by(task_id="TASK-UNRELATED-AUTH").one().status == "failed"
        assert db.query(PlatformAgentTask).filter_by(task_id="TASK-COMPLETED-AUTH").one().status == "completed"
        assert db.query(PlatformAgentTask).filter_by(task_id="TASK-WRONG-FAILURE").one().status == "failed"
        task.status = "failed"
        task.error_message = "authorization_resume_required"
        task.attempts = task.max_attempts
        db.commit()
    finally:
        db.close()
    exhausted = runtime.load_mission_run(accepted["workflow_run_id"])
    exhausted["error"] = {"classification": "authorization_resume_required"}
    assert runtime._resume_authorization_if_possible(exhausted) is False

    state = runtime.load_mission_run(accepted["workflow_run_id"])
    observer = runtime._progress_observer(state)
    observer(stage="planning", status="running", summary="Planning started.")
    observer(stage="planning", status="completed", summary="Planning completed.")
    observer(stage="change_set_generation", status="running", summary="Change set generation started.")
    runtime._advance(state, "change_set_ready", "Change set ready.")
    terminal = runtime.load_mission_run(accepted["workflow_run_id"])
    assert terminal["current_stage"] == "change_set_ready"
    with patch.object(runtime, "require_founder", return_value={"authorized": True}), patch.object(runtime, "_activate_canonical_worker") as terminal_worker:
        terminal_status = runtime.get_mission_run_status({"token": "restored-session", "workflow_run_id": accepted["workflow_run_id"]})
    assert terminal_status["progress"]["terminal"] is True
    terminal_worker.assert_not_called()
    latest = runtime.find_latest_mission_run(mission_id)
    assert latest["workflow_run_id"] == accepted["workflow_run_id"]

    sources = {"verification_service": {}, "deployment_manager": {}, "github_executor": {}, "engineering_manager": {}, "rollback_manager": {}, "board_room": {}}
    status = _derive_status(sources, {}, terminal)
    recommendation = _recommendation(status, sources, terminal)
    progress = _mission_progress(status, sources, {}, terminal)
    projection = _durable_auto_progress(terminal)
    assert status == "Change Set Ready" and recommendation["action"] == "Review the prepared change set"
    assert progress < 100 and projection["mode"] == "durable-runtime-projection"
    observed = MissionAggregator().snapshot()["missions"][0]
    assert observed["mission_id"] == mission_id and observed["status"] == "Change Set Ready"
    unlinked_status = _derive_status(sources, {}, {})
    assert unlinked_status == "Not Linked" and _mission_progress(unlinked_status, sources, {}, {}) is None
    assert "founder-session" not in str(accepted) and "restored-session" not in str(resumed)
    print("durable worker progress and mission reconciliation ok")


if __name__ == "__main__":
    main()
