from __future__ import annotations

import json
import time
from unittest.mock import patch

import app.platform.execution.service as execution_service
from app.platform.board_room.natural_conversation_check import PRODUCTION_REQUEST
from app.platform.server import app


def _authorized(_: dict) -> dict:
    return {"authorized": True, "role": "founder", "email": "founder@example.com"}


def _route(path: str):
    return next(route.endpoint for route in app.routes if getattr(route, "path", None) == path and "POST" in getattr(route, "methods", set()))


def main() -> None:
    execution_service._ACTIVE_MISSION = None
    action_states: dict[str, dict] = {}
    mission_runs: dict[str, dict] = {}

    def load_action(context_id: str):
        value = action_states.get(context_id)
        return json.loads(json.dumps(value)) if value else None

    def save_action(state: dict) -> None:
        action_states[state["action_context_id"]] = json.loads(json.dumps(state))

    def load_run(run_id: str, **_: object):
        value = mission_runs.get(run_id)
        return {**json.loads(json.dumps(value)), "found": True} if value else {"found": False, "workflow_run_id": run_id}

    def save_run(state: dict) -> None:
        mission_runs[state["workflow_run_id"]] = json.loads(json.dumps(state))

    chat = _route("/mission-control/operating-console/chat")
    action = _route("/mission-control/operating-console/action")
    with (
        patch("app.platform.operating_console.service.require_founder", _authorized),
        patch("app.platform.operating_console.action_service.require_founder", _authorized),
        patch("app.platform.operating_console.action_service._load_state", side_effect=load_action),
        patch("app.platform.operating_console.action_service._persist_state", side_effect=save_action),
        patch("app.platform.operating_console.mission_run_service.load_mission_run", side_effect=load_run),
        patch("app.platform.operating_console.mission_run_service._persist", side_effect=save_run),
        patch("app.platform.operating_console.mission_run_service._enqueue") as enqueue,
        patch("app.platform.operating_console.mission_run_service._activate_canonical_worker") as dispatch,
        patch("app.platform.founder_approval.service._write_artifacts", side_effect=AssertionError("approval must not write repository artifacts")),
    ):
        proposal = chat({"token": "founder", "message": PRODUCTION_REQUEST, "provider": "openai", "model": "gpt-5.5"})
        buttons = proposal["action_metadata"]["action_buttons"]
        assert [item["label"] for item in buttons] == ["Review Mission Scope", "Approve Mission", "Save Mission"]
        approve_payload = next(item["payload"] for item in buttons if item["label"] == "Approve Mission")

        started = time.monotonic()
        accepted = action({"token": "founder", **approve_payload})
        assert time.monotonic() - started < 1
        assert accepted["status"] == "accepted"
        assert accepted["mission_id"].startswith("MISSION-")
        assert accepted["workflow_run_id"].startswith("MISSION-RUN-")
        assert accepted["worker_dispatch"]["transport"] == "PlatformAgentTask + Agent Worker"
        assert execution_service._ACTIVE_MISSION is None

        repeated = action({"token": "founder", **approve_payload})
        assert repeated["workflow_run_id"] == accepted["workflow_run_id"]
        assert repeated["reused"] is True
        assert len(mission_runs) == 1
        enqueue.assert_called_once()
        assert dispatch.call_count == 2
        assert all(accepted["governance"][key] is False for key in ("repository_mutation", "branch_creation", "commit", "push", "pull_request_creation", "merge", "deployment", "rollback", "traffic_shift"))

        tampered = json.loads(json.dumps(approve_payload))
        tampered["action_context"]["founder_request"] = "Tampered request"
        rejected = action({"token": "founder", **tampered})
        assert rejected["failed_stage"] == "action_context"

    print("board room governed action flow ok")


if __name__ == "__main__":
    main()
