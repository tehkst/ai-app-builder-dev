import json

import app.platform.services.module_rollout_gate_service as rollout_service
import app.platform.services.self_build_module_request_service as request_service


WORKFLOW_RUN_ID = "v79-linked-workflow"

_LOOP_STATUS = "waiting_for_repair_approval"


def _fake_self_healing_loop(workflow_run_id):
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": "self_healing_loop_coordinator_v77_approval_preserving",
        "loop_status": _LOOP_STATUS,
        "next_required_action": "review_rerun_result" if _LOOP_STATUS == "self_healing_loop_completed" else "approve_or_reject_repair_plan",
        "summary": "Fake loop status for V79 rollout gate check.",
        "safety_flags": {
            "approval_gates_preserved": True,
            "auto_approval_performed": False,
            "repair_applied_by_loop": False,
            "restore_executed": False,
            "module_rollout_performed": False,
            "install_packages_performed": False,
        },
    }


def _safe(result, *, handoff_checked_expected=False, approval_recorded_expected=False):
    flags = result.get("safety_flags") or {}
    return (
        flags.get("module_rollout_gate_checked") is True
        and flags.get("rollout_gate_only") is True
        and flags.get("rollout_eligibility_checked") is True
        and flags.get("handoff_checked") is handoff_checked_expected
        and flags.get("rollout_approval_recorded") is approval_recorded_expected
        and flags.get("rollout_execution_performed") is False
        and flags.get("module_rollout_performed") is False
        and flags.get("production_file_write_performed") is False
        and flags.get("live_module_modified") is False
        and flags.get("auto_approval_performed") is False
        and flags.get("approval_bypass_performed") is False
        and flags.get("generated_code_execution_performed") is False
        and flags.get("runtime_server_started") is False
        and flags.get("install_packages_performed") is False
        and flags.get("repair_applied") is False
        and flags.get("unapproved_repair_applied") is False
        and flags.get("restore_executed") is False
    )


def _create_request(*, linked=True):
    created = request_service.create_self_build_module_request(
        module_name="Rollout Candidate",
        module_goal="Validate rollout gate only.",
        requested_by="smoke_check",
        acceptance_criteria=["No actual rollout", "Approval gate visible"],
    )
    request_id = (created.get("request") or {}).get("request_id")
    if linked:
        request_service.link_self_build_module_request_to_workflow(
            request_id=request_id,
            workflow_run_id=WORKFLOW_RUN_ID,
            linked_by="smoke_check",
        )
    return request_id


def run_check():
    global _LOOP_STATUS

    request_service.reset_self_build_module_requests_for_check()
    rollout_service.reset_module_rollout_gate_for_check()
    original_request_inspect = request_service.inspect_self_healing_loop
    original_rollout_inspect = rollout_service.inspect_self_build_module_request_handoff
    request_service.inspect_self_healing_loop = _fake_self_healing_loop

    def _patched_rollout_handoff(request_id):
        return request_service.inspect_self_build_module_request_handoff(request_id)

    rollout_service.inspect_self_build_module_request_handoff = _patched_rollout_handoff

    checks = {}
    samples = {}

    try:
        missing = rollout_service.inspect_module_rollout_gate("missing-request")
        checks["missing_not_found"] = missing.get("eligibility_status") == "not_found" and missing.get("eligible") is False
        checks["missing_safe"] = _safe(missing, handoff_checked_expected=False)

        unlinked_request_id = _create_request(linked=False)
        unlinked = rollout_service.inspect_module_rollout_gate(unlinked_request_id)
        checks["unlinked_not_eligible"] = unlinked.get("eligible") is False and unlinked.get("eligibility_status") == "not_eligible"
        checks["unlinked_waits_for_workflow"] = "workflow_run_id" in " ".join(unlinked.get("eligibility_reasons") or [])
        checks["unlinked_safe"] = _safe(unlinked, handoff_checked_expected=False)

        _LOOP_STATUS = "waiting_for_repair_approval"
        blocked_request_id = _create_request(linked=True)
        blocked = rollout_service.inspect_module_rollout_gate(blocked_request_id)
        checks["blocked_not_eligible"] = blocked.get("eligible") is False and blocked.get("loop_status") == "waiting_for_repair_approval"
        checks["blocked_safe"] = _safe(blocked, handoff_checked_expected=True)

        blocked_approval = rollout_service.approve_module_rollout(
            request_id=blocked_request_id,
            approved_by="smoke_check",
            reason="Should be blocked before loop is healthy.",
        )
        checks["approval_blocked_when_not_eligible"] = blocked_approval.get("rollout_status") == "approval_blocked_not_eligible"
        checks["blocked_approval_no_record"] = blocked_approval.get("approval_record") is None
        checks["blocked_approval_safe"] = _safe(blocked_approval, handoff_checked_expected=True, approval_recorded_expected=False)
        checks["blocked_approval_history"] = [event.get("action") for event in blocked_approval.get("history") or []] == ["approval_blocked_not_eligible"]

        _LOOP_STATUS = "self_healing_loop_completed"
        eligible_request_id = _create_request(linked=True)
        eligible = rollout_service.inspect_module_rollout_gate(eligible_request_id)
        checks["completed_loop_eligible"] = eligible.get("eligible") is True
        checks["eligible_status"] = eligible.get("eligibility_status") == "eligible_for_rollout_approval"
        checks["eligible_rollout_waiting"] = eligible.get("rollout_status") == "waiting_for_rollout_approval"
        checks["eligible_safe"] = _safe(eligible, handoff_checked_expected=True)

        approved = rollout_service.approve_module_rollout(
            request_id=eligible_request_id,
            approved_by="smoke_check",
            reason="Eligible and approved for future rollout gate.",
        )
        approval_record = approved.get("approval_record") or {}
        checks["approval_recorded_when_eligible"] = approved.get("rollout_status") == "rollout_approved" and approval_record.get("approved") is True
        checks["approval_does_not_allow_execution"] = approval_record.get("rollout_execution_allowed") is False and approval_record.get("rollout_execution_performed") is False
        checks["approval_safe"] = _safe(approved, handoff_checked_expected=True, approval_recorded_expected=True)

        history_after_approval = rollout_service.get_module_rollout_history(eligible_request_id)
        checks["history_has_approval"] = [event.get("action") for event in history_after_approval.get("history") or []] == ["rollout_approved"]
        checks["history_safe"] = _safe(history_after_approval, handoff_checked_expected=False)

        rejected = rollout_service.reject_module_rollout(
            request_id=eligible_request_id,
            rejected_by="smoke_check",
            reason="Reject after approval for history test.",
        )
        rejection_record = rejected.get("approval_record") or {}
        checks["rejection_recorded"] = rejected.get("rollout_status") == "rollout_rejected" and rejection_record.get("rejected") is True
        checks["rejection_does_not_execute"] = rejection_record.get("rollout_execution_allowed") is False and rejection_record.get("rollout_execution_performed") is False
        checks["rejection_safe"] = _safe(rejected, handoff_checked_expected=True, approval_recorded_expected=True)

        final_history = rollout_service.get_module_rollout_history(eligible_request_id)
        checks["history_has_approval_and_rejection"] = [event.get("action") for event in final_history.get("history") or []] == [
            "rollout_approved",
            "rollout_rejected",
        ]
        checks["final_history_safe"] = _safe(final_history, handoff_checked_expected=False)

        _LOOP_STATUS = "healthy_no_repair_needed"
        healthy_request_id = _create_request(linked=True)
        healthy = rollout_service.inspect_module_rollout_gate(healthy_request_id)
        checks["healthy_loop_eligible"] = healthy.get("eligible") is True and healthy.get("loop_status") == "healthy_no_repair_needed"
        checks["healthy_safe"] = _safe(healthy, handoff_checked_expected=True)

        samples = {
            "missing": missing,
            "unlinked": unlinked,
            "blocked": blocked,
            "blocked_approval": blocked_approval,
            "eligible": eligible,
            "approved": approved,
            "rejected": rejected,
            "final_history": final_history,
            "healthy": healthy,
        }
    finally:
        request_service.inspect_self_healing_loop = original_request_inspect
        rollout_service.inspect_self_build_module_request_handoff = original_rollout_inspect
        request_service.reset_self_build_module_requests_for_check()
        rollout_service.reset_module_rollout_gate_for_check()

    return {
        "check": "module_rollout_gate_check",
        "passed": all(checks.values()),
        "checks": checks,
        "sample": samples,
    }


if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
