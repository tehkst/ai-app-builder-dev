from __future__ import annotations

import importlib
from typing import Any, Dict

import app.platform.services.module_rollout_gate_service as rollout_service
import app.platform.services.self_build_module_request_service as request_service
from app.platform.services.persistent_state_store_service import (
    V82_PERSISTENT_STATE_SAFETY_MODE,
    get_module_rollout_decision,
    get_self_build_module_request_record,
    list_module_rollout_events,
    list_self_build_module_request_events,
    reset_v82_persistent_state_for_check,
)

WORKFLOW_RUN_ID = "v82-persistent-state-workflow"


def _fake_self_healing_loop(*, workflow_run_id: str) -> Dict[str, Any]:
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "loop_status": "self_healing_loop_completed",
        "next_required_action": "rollout_approval_gate",
        "safety_mode": "self_healing_loop_coordinator_v77_approval_preserving",
        "safety_flags": {
            "approval_gates_preserved": True,
            "auto_approval_performed": False,
            "approval_bypass_performed": False,
            "module_rollout_performed": False,
            "rollout_execution_performed": False,
        },
    }


def _safe_request_flags(result: Dict[str, Any]) -> bool:
    flags = result.get("safety_flags") or {}
    return (
        flags.get("request_tracking_only") is True
        and flags.get("persistent_state_store_used") is True
        and flags.get("workflow_created_by_request_service") is False
        and flags.get("generated_files_written") is False
        and flags.get("generated_code_execution_performed") is False
        and flags.get("runtime_server_started") is False
        and flags.get("auto_approval_performed") is False
        and flags.get("approval_bypass_performed") is False
        and flags.get("module_rollout_performed") is False
    )


def _safe_rollout_flags(result: Dict[str, Any], *, approval_recorded: bool) -> bool:
    flags = result.get("safety_flags") or {}
    return (
        flags.get("rollout_gate_only") is True
        and flags.get("persistent_state_store_used") is True
        and flags.get("rollout_approval_recorded") is approval_recorded
        and flags.get("rollout_execution_performed") is False
        and flags.get("module_rollout_performed") is False
        and flags.get("production_file_write_performed") is False
        and flags.get("live_module_modified") is False
        and flags.get("auto_approval_performed") is False
        and flags.get("approval_bypass_performed") is False
        and flags.get("generated_code_execution_performed") is False
        and flags.get("runtime_server_started") is False
    )


def run_persistent_state_store_check() -> Dict[str, Any]:
    checks: Dict[str, bool] = {}
    samples: Dict[str, Any] = {}

    reset_v82_persistent_state_for_check()

    original_request_loop = request_service.inspect_self_healing_loop
    request_service.inspect_self_healing_loop = _fake_self_healing_loop
    try:
        created = request_service.create_self_build_module_request(
            module_name="Persistent Approval Checklist",
            module_goal="Prove V82 stores module requests in the database.",
            requested_by="smoke_check",
            acceptance_criteria=["Request persists", "Rollout gate remains approval only"],
            notes="V82 persistence check only.",
        )
        request_id = (created.get("request") or {}).get("request_id")
        linked = request_service.link_self_build_module_request_to_workflow(
            request_id=request_id,
            workflow_run_id=WORKFLOW_RUN_ID,
            linked_by="smoke_check",
        )
        inspected = request_service.inspect_self_build_module_request_handoff(request_id)
        gate = rollout_service.inspect_module_rollout_gate(request_id)
        approved = rollout_service.approve_module_rollout(
            request_id=request_id,
            approved_by="smoke_check",
            reason="V82 persistence approval record only.",
        )

        persisted_request = get_self_build_module_request_record(request_id)
        persisted_request_events = list_self_build_module_request_events(request_id)
        persisted_decision = get_module_rollout_decision(request_id)
        persisted_rollout_events = list_module_rollout_events(request_id)

        reloaded_request_service = importlib.reload(request_service)
        reloaded_rollout_service = importlib.reload(rollout_service)
        reloaded_request_service.inspect_self_healing_loop = _fake_self_healing_loop
        reloaded_request = reloaded_request_service.get_self_build_module_request(request_id)
        reloaded_gate = reloaded_rollout_service.inspect_module_rollout_gate(request_id)
        reloaded_history = reloaded_rollout_service.get_module_rollout_history(request_id)

        checks["request_created"] = created.get("success") is True and bool(request_id)
        checks["request_linked"] = (linked.get("request") or {}).get("workflow_run_id") == WORKFLOW_RUN_ID
        checks["handoff_eligible_loop"] = (inspected.get("self_healing_loop") or {}).get("loop_status") == "self_healing_loop_completed"
        checks["gate_waits_for_approval"] = gate.get("eligible") is True and gate.get("rollout_status") == "waiting_for_rollout_approval"
        checks["approval_persisted"] = approved.get("rollout_status") == "rollout_approved" and (approved.get("approval_record") or {}).get("approved") is True
        checks["request_db_record_exists"] = persisted_request is not None and persisted_request.get("request_id") == request_id
        checks["request_events_persisted"] = [event.get("action") for event in persisted_request_events] == ["created", "linked_to_workflow", "handoff_checked", "handoff_checked", "handoff_checked"]
        checks["rollout_decision_persisted"] = persisted_decision is not None and persisted_decision.get("approval_status") == "rollout_approved"
        checks["rollout_events_persisted"] = [event.get("action") for event in persisted_rollout_events] == ["rollout_approved"]
        checks["request_survives_reload"] = (reloaded_request.get("request") or {}).get("request_id") == request_id
        checks["rollout_decision_survives_reload"] = (reloaded_gate.get("approval_record") or {}).get("approval_status") == "rollout_approved"
        checks["rollout_history_survives_reload"] = [event.get("action") for event in (reloaded_history.get("history") or [])] == ["rollout_approved"]
        checks["request_safety"] = all(
            _safe_request_flags(result)
            for result in [created, linked, inspected, reloaded_request]
        )
        checks["rollout_safety"] = (
            _safe_rollout_flags(gate, approval_recorded=False)
            and _safe_rollout_flags(approved, approval_recorded=True)
            and _safe_rollout_flags(reloaded_gate, approval_recorded=True)
        )
        checks["rollout_execution_disabled"] = (
            (approved.get("approval_record") or {}).get("rollout_execution_allowed") is False
            and (approved.get("approval_record") or {}).get("rollout_execution_performed") is False
            and (persisted_decision or {}).get("rollout_execution_allowed") is False
            and (persisted_decision or {}).get("rollout_execution_performed") is False
        )

        samples = {
            "request_id": request_id,
            "created": created,
            "gate": gate,
            "approved": approved,
            "persisted_request": persisted_request,
            "persisted_decision": persisted_decision,
            "reloaded_gate": reloaded_gate,
        }
    finally:
        request_service.inspect_self_healing_loop = original_request_loop

    passed = all(checks.values())
    return {
        "check": "persistent_state_store_check",
        "milestone": "V82 — Persistent State Store",
        "passed": passed,
        "safety_mode": V82_PERSISTENT_STATE_SAFETY_MODE,
        "checks": checks,
        "samples": samples,
    }


def main() -> int:
    result = run_persistent_state_store_check()
    print(result)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
