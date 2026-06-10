# Split from the legacy module to keep each Python file under 200 lines.
import json
import app.platform.services.internal_dogfooding_module_service as dogfood_service
import app.platform.services.module_rollout_gate_service as rollout_service
import app.platform.services.self_build_module_request_service as request_service
WORKFLOW_RUN_ID = "v80-dogfooding-workflow"
_LOOP_STATUS = "waiting_for_repair_approval"

def run_check():
    global _LOOP_STATUS

    request_service.reset_self_build_module_requests_for_check()
    rollout_service.reset_module_rollout_gate_for_check()
    dogfood_service.reset_internal_dogfooding_module_for_check()
    original_request_inspect, original_rollout_handoff = _patch_loop()

    checks = {}
    sample = {}

    try:
        created = dogfood_service.create_internal_dogfooding_module_request(
            requested_by="smoke_check",
        )
        request_id = created.get("request_id")
        request_record = ((created.get("module_request") or {}).get("request") or {})
        checks["created_success"] = created.get("success") is True and bool(request_id)
        checks["created_default_module"] = request_record.get("module_name") == "Internal Approval Checklist"
        checks["created_acceptance_criteria"] = "Does not execute rollout" in (request_record.get("acceptance_criteria") or [])
        checks["created_history"] = [event.get("action") for event in created.get("history") or []] == ["dogfooding_module_request_created"]
        checks["created_safe"] = _safe(created)

        linked = dogfood_service.link_internal_dogfooding_module_to_workflow(
            request_id=request_id,
            workflow_run_id=WORKFLOW_RUN_ID,
            linked_by="smoke_check",
        )
        linked_request = ((linked.get("module_request") or {}).get("request") or {})
        checks["linked_success"] = linked_request.get("workflow_run_id") == WORKFLOW_RUN_ID
        checks["linked_history"] = [event.get("action") for event in linked.get("history") or []] == [
            "dogfooding_module_request_created",
            "dogfooding_module_linked_to_workflow",
        ]
        checks["linked_safe"] = _safe(linked)

        _LOOP_STATUS = "waiting_for_repair_approval"
        inspected_blocked = dogfood_service.inspect_internal_dogfooding_module(request_id=request_id)
        blocked_gate = inspected_blocked.get("rollout_gate") or {}
        checks["inspect_blocked_handoff"] = ((inspected_blocked.get("handoff") or {}).get("self_healing_loop") or {}).get("loop_status") == "waiting_for_repair_approval"
        checks["inspect_blocked_gate"] = blocked_gate.get("eligible") is False and blocked_gate.get("eligibility_status") == "not_eligible"
        checks["inspect_blocked_safe"] = _safe(inspected_blocked, rollout_gate_checked=True)
        checks["inspect_blocked_gate_safe"] = _gate_safe(blocked_gate)

        blocked_decision = dogfood_service.decide_internal_dogfooding_rollout(
            request_id=request_id,
            decision="approve",
            decided_by="smoke_check",
            reason="Should be blocked while loop is waiting for repair approval.",
        )
        blocked_decision_result = blocked_decision.get("decision_result") or {}
        checks["blocked_approval_status"] = blocked_decision_result.get("rollout_status") == "approval_blocked_not_eligible"
        checks["blocked_approval_no_record"] = blocked_decision_result.get("approval_record") is None
        checks["blocked_decision_safe"] = _safe(blocked_decision, rollout_gate_checked=True, rollout_decision_recorded=True)
        checks["blocked_decision_gate_safe"] = _gate_safe(blocked_decision_result, approval_recorded=False)

        _LOOP_STATUS = "self_healing_loop_completed"
        eligible_request = dogfood_service.create_internal_dogfooding_module_request(
            requested_by="smoke_check",
            workflow_run_id=WORKFLOW_RUN_ID,
        )
        eligible_request_id = eligible_request.get("request_id")
        inspected_eligible = dogfood_service.inspect_internal_dogfooding_module(request_id=eligible_request_id)
        eligible_gate = inspected_eligible.get("rollout_gate") or {}
        checks["eligible_inspect_loop_complete"] = eligible_gate.get("loop_status") == "self_healing_loop_completed"
        checks["eligible_inspect_gate"] = eligible_gate.get("eligible") is True and eligible_gate.get("rollout_status") == "waiting_for_rollout_approval"
        checks["eligible_inspect_safe"] = _safe(inspected_eligible, rollout_gate_checked=True)
        checks["eligible_gate_safe"] = _gate_safe(eligible_gate)

        approved = dogfood_service.decide_internal_dogfooding_rollout(
            request_id=eligible_request_id,
            decision="approve",
            decided_by="smoke_check",
            reason="Eligible dogfooding module gate approval.",
        )
        approved_result = approved.get("decision_result") or {}
        approval_record = approved_result.get("approval_record") or {}
        checks["approval_recorded"] = approved_result.get("rollout_status") == "rollout_approved" and approval_record.get("approved") is True
        checks["approval_no_execution"] = approval_record.get("rollout_execution_allowed") is False and approval_record.get("rollout_execution_performed") is False
        checks["approval_safe"] = _safe(approved, rollout_gate_checked=True, rollout_decision_recorded=True)
        checks["approval_gate_safe"] = _gate_safe(approved_result, approval_recorded=True)

        rejected = dogfood_service.decide_internal_dogfooding_rollout(
            request_id=eligible_request_id,
            decision="reject",
            decided_by="smoke_check",
            reason="Reject after approval for decision history test.",
        )
        rejected_result = rejected.get("decision_result") or {}
        rejection_record = rejected_result.get("approval_record") or {}
        checks["rejection_recorded"] = rejected_result.get("rollout_status") == "rollout_rejected" and rejection_record.get("rejected") is True
        checks["rejection_no_execution"] = rejection_record.get("rollout_execution_allowed") is False and rejection_record.get("rollout_execution_performed") is False
        checks["rejection_safe"] = _safe(rejected, rollout_gate_checked=True, rollout_decision_recorded=True)
        checks["rejection_gate_safe"] = _gate_safe(rejected_result, approval_recorded=True)

        invalid = dogfood_service.decide_internal_dogfooding_rollout(
            request_id=eligible_request_id,
            decision="maybe",
            decided_by="smoke_check",
            reason="Invalid decision should not execute anything.",
        )
        invalid_result = invalid.get("decision_result") or {}
        checks["invalid_decision_safe_status"] = invalid_result.get("rollout_status") == "invalid_decision"
        checks["invalid_decision_safe"] = _safe(invalid, rollout_gate_checked=True, rollout_decision_recorded=False)

        history = dogfood_service.get_internal_dogfooding_module_history(eligible_request_id)
        history_actions = [event.get("action") for event in history.get("history") or []]
        checks["history_contains_create_inspect_decisions"] = history_actions == [
            "dogfooding_module_request_created",
            "dogfooding_module_inspected",
            "dogfooding_rollout_approval_recorded",
            "dogfooding_rollout_rejection_recorded",
            "dogfooding_rollout_decision_invalid",
        ]
        checks["history_safe"] = _safe(history)

        sample = {
            "created": created,
            "linked": linked,
            "inspected_blocked": inspected_blocked,
            "blocked_decision": blocked_decision,
            "eligible_request": eligible_request,
            "inspected_eligible": inspected_eligible,
            "approved": approved,
            "rejected": rejected,
            "invalid": invalid,
            "history": history,
        }
    finally:
        _restore_loop(original_request_inspect, original_rollout_handoff)
        request_service.reset_self_build_module_requests_for_check()
        rollout_service.reset_module_rollout_gate_for_check()
        dogfood_service.reset_internal_dogfooding_module_for_check()

    return {
        "check": "internal_dogfooding_module_check",
        "passed": all(checks.values()),
        "checks": checks,
        "sample": sample,
    }
