# Split from the legacy module to keep each Python file under 200 lines.
import json
import app.platform.services.internal_dogfooding_module_service as dogfood_service
import app.platform.services.module_rollout_gate_service as rollout_service
import app.platform.services.self_build_module_request_service as request_service
WORKFLOW_RUN_ID = "v80-dogfooding-workflow"
_LOOP_STATUS = "waiting_for_repair_approval"

def _fake_self_healing_loop(workflow_run_id):
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": "self_healing_loop_coordinator_v77_approval_preserving",
        "loop_status": _LOOP_STATUS,
        "next_required_action": "review_rerun_result" if _LOOP_STATUS == "self_healing_loop_completed" else "approve_or_reject_repair_plan",
        "summary": "Fake loop status for V80 internal dogfooding check.",
        "safety_flags": {
            "approval_gates_preserved": True,
            "auto_approval_performed": False,
            "repair_applied_by_loop": False,
            "restore_executed": False,
            "module_rollout_performed": False,
            "install_packages_performed": False,
        },
    }

def _safe(result, *, rollout_gate_checked=False, rollout_decision_recorded=False):
    flags = result.get("safety_flags") or {}
    return (
        flags.get("internal_dogfooding_checked") is True
        and flags.get("dogfooding_demonstration_only") is True
        and flags.get("module_request_created") is True
        and flags.get("rollout_gate_checked") is rollout_gate_checked
        and flags.get("rollout_decision_recorded") is rollout_decision_recorded
        and flags.get("generated_files_written") is False
        and flags.get("filesystem_write_performed") is False
        and flags.get("production_file_write_performed") is False
        and flags.get("live_module_modified") is False
        and flags.get("generated_code_execution_performed") is False
        and flags.get("runtime_server_started") is False
        and flags.get("install_packages_performed") is False
        and flags.get("auto_approval_performed") is False
        and flags.get("approval_bypass_performed") is False
        and flags.get("repair_applied") is False
        and flags.get("unapproved_repair_applied") is False
        and flags.get("restore_executed") is False
        and flags.get("module_rollout_performed") is False
        and flags.get("rollout_execution_performed") is False
    )

def _gate_safe(result, *, approval_recorded=False):
    flags = result.get("safety_flags") or {}
    return (
        flags.get("module_rollout_gate_checked") is True
        and flags.get("rollout_gate_only") is True
        and flags.get("rollout_eligibility_checked") is True
        and flags.get("rollout_approval_recorded") is approval_recorded
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

def _patch_loop():
    original_request_inspect = request_service.inspect_self_healing_loop
    original_rollout_handoff = rollout_service.inspect_self_build_module_request_handoff
    request_service.inspect_self_healing_loop = _fake_self_healing_loop

    def _patched_rollout_handoff(request_id):
        return request_service.inspect_self_build_module_request_handoff(request_id)

    rollout_service.inspect_self_build_module_request_handoff = _patched_rollout_handoff
    return original_request_inspect, original_rollout_handoff

def _restore_loop(original_request_inspect, original_rollout_handoff):
    request_service.inspect_self_healing_loop = original_request_inspect
    rollout_service.inspect_self_build_module_request_handoff = original_rollout_handoff
