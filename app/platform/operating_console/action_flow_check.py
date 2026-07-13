from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import app.platform.execution.service as execution_service
from app.platform.board_room.natural_conversation_check import PRODUCTION_REQUEST
from app.platform.journey_inspection.service import inspect_mission_journey
from app.platform.server import app


def _authorized(_: dict) -> dict:
    return {"authorized": True, "role": "founder", "email": "founder@example.com"}


def _route(path: str):
    return next(route.endpoint for route in app.routes if getattr(route, "path", None) == path and "POST" in getattr(route, "methods", set()))


def _model(payload: dict) -> dict:
    prompt = json.loads(payload["prompt"])
    mission_id = prompt["mission_id"]
    files = []
    for item in prompt["repository_context"]:
        if not item.get("target"):
            continue
        path = str(item["path"])
        content = Path(path).read_text() if Path(path).exists() else "# Mission implementation\n"
        content += "\n// Approved mission change prepared for review.\n" if path.endswith(".js") else "\n# Approved mission change prepared for review.\n"
        files.append({"path": path, "operation": item["operation"], "content": content, "rationale": "Preserve the repository-grounded target while preparing the approved change set.", "source_evidence": [path], "confidence": "high"})
    return {"status": "completed", "provider": "openai", "model": "gpt-5.5", "output_text": json.dumps({"mission_id": mission_id, "files": files, "assumptions": [], "risks": ["UI regression risk requires dashboard validation."]})}


def _invalid_model(payload: dict) -> dict:
    prompt = json.loads(payload["prompt"])
    files = []
    for item in prompt["repository_context"]:
        if not item.get("target"):
            continue
        path = str(item["path"])
        content = "// TODO implement here\n" if path.endswith(".js") else "# TODO implement here\n"
        files.append({"path": path, "operation": item["operation"], "content": content, "rationale": "Change it.", "source_evidence": [path], "confidence": "unknown"})
    output = {"mission_id": prompt["mission_id"], "files": files, "assumptions": [], "risks": []}
    return {"status": "completed", "provider": "openai", "model": "gpt-5.5", "output_text": json.dumps(output)}


def main() -> None:
    execution_service._ACTIVE_MISSION = None
    persisted: dict[str, dict] = {}

    def load(context_id: str):
        value = persisted.get(context_id)
        return json.loads(json.dumps(value)) if value else None

    def save(state: dict):
        persisted[state["action_context_id"]] = json.loads(json.dumps(state))

    chat = _route("/mission-control/operating-console/chat")
    action = _route("/mission-control/operating-console/action")

    with (
        patch("app.platform.operating_console.service.require_founder", _authorized),
        patch("app.platform.operating_console.action_service.require_founder", _authorized),
        patch("app.platform.execution.service.require_founder", _authorized),
        patch("app.platform.planning.service.require_founder", _authorized),
        patch("app.platform.engineering_manager.service.require_founder", _authorized),
        patch("app.platform.operating_console.action_service._load_state", side_effect=load),
        patch("app.platform.operating_console.action_service._persist_state", side_effect=save),
        patch("app.platform.founder_approval.service._write_artifacts", side_effect=AssertionError("mission approval must not write repository artifacts")),
        patch("app.platform.execution.orchestrator.generate_engineering_plan", wraps=__import__("app.platform.planning.service", fromlist=["generate_engineering_plan"]).generate_engineering_plan) as planning,
        patch("app.platform.execution.orchestrator.create_engineering_breakdown", wraps=__import__("app.platform.engineering_manager.service", fromlist=["create_engineering_breakdown"]).create_engineering_breakdown) as handoff,
        patch("app.platform.engineering.change_set_service.invoke_ai", side_effect=_model) as model,
    ):
        proposal = chat({"token": "founder", "message": PRODUCTION_REQUEST, "provider": "openai", "model": "gpt-5.5"})
        buttons = proposal["action_metadata"]["action_buttons"]
        assert [item["label"] for item in buttons] == ["Review Mission Scope", "Approve Mission", "Save Mission"]

        review_payload = next(item["payload"] for item in buttons if item["label"] == "Review Mission Scope")
        review = action({"token": "founder", **review_payload})
        assert review["status"] == "mission-scope-ready"
        assert all(key in review["scope"] for key in ("objective", "acceptance_criteria", "in_scope", "out_of_scope", "governance_boundaries", "expected_next_action"))
        assert execution_service._ACTIVE_MISSION is None

        continue_payload = dict(review_payload, action="continue_planning")
        blocked = action({"token": "founder", **continue_payload})
        assert blocked["status"] == "blocked"
        assert blocked["failed_stage"] == "founder_approval"
        assert execution_service._ACTIVE_MISSION is None

        save_payload = next(item["payload"] for item in buttons if item["label"] == "Save Mission")
        saved = action({"token": "founder", **save_payload})
        assert saved["status"] == "mission-proposal-saved"
        assert "still awaiting scope approval" in saved["board_room_response"]
        assert execution_service._ACTIVE_MISSION is None

        approve_payload = next(item["payload"] for item in buttons if item["label"] == "Approve Mission")
        approved = action({"token": "founder", **approve_payload})
        mission_id = approved["mission_id"]
        assert mission_id.startswith("MISSION-")
        assert approved["status"] == "change_set_ready", approved
        assert approved["planning_result"]["plan"]["mission_id"] == mission_id
        assert approved["engineering_handoff"]["mission_id"] == mission_id
        assert approved["executable_change_set"]["mission_id"] == mission_id
        assert approved["executable_change_set"]["change_set_status"] == "change_set_ready"
        assert "Code changes prepared — awaiting engineering execution approval." in approved["board_room_response"]
        assert [item["label"] for item in approved["action_metadata"]["action_buttons"]] == ["Review Proposed Changes", "Authorize Engineering Execution"]
        assert all(approved["governance"][key] is False for key in ("repository_mutation", "branch_creation", "commit", "push", "pull_request_creation", "merge", "deployment", "rollback", "traffic_shift"))

        repeated = action({"token": "founder", **approve_payload})
        assert repeated["mission_id"] == mission_id
        assert repeated["planning_result"]["plan"]["plan_id"] == approved["planning_result"]["plan"]["plan_id"]
        assert repeated["engineering_handoff"]["breakdown_id"] == approved["engineering_handoff"]["breakdown_id"]
        assert repeated["executable_change_set"]["source_plan_id"] == approved["executable_change_set"]["source_plan_id"]
        assert planning.call_count == 1
        assert handoff.call_count == 1
        assert model.call_count == 1

        with patch("app.platform.engineering.change_set_service.invoke_ai", side_effect=_invalid_model) as invalid_model:
            blocked_proposal = chat({"token": "founder", "message": PRODUCTION_REQUEST + "\nAdditional scope: verify the blocked change-set repair path.", "provider": "openai", "model": "gpt-5.5"})
            blocked_approve = next(item["payload"] for item in blocked_proposal["action_metadata"]["action_buttons"] if item["label"] == "Approve Mission")
            blocked_result = action({"token": "founder", **blocked_approve})
            blocked_mission_id = blocked_result["mission_id"]
            blocked_plan_id = blocked_result["planning_result"]["plan"]["plan_id"]
            blocked_handoff_id = blocked_result["engineering_handoff"]["breakdown_id"]
            assert blocked_result["status"] == "blocked"
            assert blocked_result["blocked_stage"] == "executable_change_set"
            assert blocked_result["approval_required"] == "none"
            assert blocked_result["safe_retry_action"] == "retry_change_set"
            assert "Next approval required" not in blocked_result["board_room_response"]
            assert "No repository action was taken." in blocked_result["board_room_response"]
            blocked_labels = [item["label"] for item in blocked_result["action_metadata"]["action_buttons"]]
            assert blocked_labels == ["Retry Change Set Generation", "Review Validation Errors", "Review Mission Scope"]
            assert not {"Continue to Planning", "Approve Mission", "Authorize Engineering Execution"}.intersection(blocked_labels)
            assert invalid_model.call_count == 2

            review_errors_payload = next(item["payload"] for item in blocked_result["action_metadata"]["action_buttons"] if item["label"] == "Review Validation Errors")
            reviewed_errors = action({"token": "founder", **review_errors_payload})
            assert reviewed_errors["status"] == "validation-errors-ready"
            assert reviewed_errors["validation_errors"]
            assert all(item.get("path") for item in reviewed_errors["validation_errors"] if item.get("candidate_index") is not None)

            retry_payload = next(item["payload"] for item in blocked_result["action_metadata"]["action_buttons"] if item["label"] == "Retry Change Set Generation")
            retried = action({"token": "founder", **retry_payload})
            assert retried["mission_id"] == blocked_mission_id
            assert retried["planning_result"]["plan"]["plan_id"] == blocked_plan_id
            assert retried["engineering_handoff"]["breakdown_id"] == blocked_handoff_id
            assert retried["status"] == "blocked"
            assert invalid_model.call_count == 4
            assert planning.call_count == 2
            assert handoff.call_count == 2

        tampered = json.loads(json.dumps(approve_payload))
        tampered["action_context"]["founder_request"] = "Tampered request"
        rejected = action({"token": "founder", **tampered})
        assert rejected["failed_stage"] == "action_context"

    journey = inspect_mission_journey(blocked_mission_id)
    planning_stage = next(item for item in journey["stages"] if item["stage_id"] == "planning")
    engineering_stage = next(item for item in journey["stages"] if item["stage_id"] == "engineering_execution")
    assert planning_stage["status"] == "verified"
    assert engineering_stage["status"] == "ready"
    print("board room governed action flow ok")


if __name__ == "__main__":
    main()
