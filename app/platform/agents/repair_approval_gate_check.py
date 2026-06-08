import json

import app.platform.services.repair_approval_gate_service as approval_service


def _planned_repair(workflow_run_id):
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": "repair_plan_generator_v73_plan_only",
        "repair_plan_status": "planned",
        "repair_plan": {
            "plan_needed": True,
            "repair_kind": "source_code_repair",
            "failure_category": "syntax_error",
            "target_file_candidates": ["src/App.jsx"],
            "proposed_change_summary": "Fix syntax error in generated source file.",
            "rationale": ["src/App.jsx:1 SyntaxError: Unexpected token"],
            "confidence": 0.75,
            "approval_requirements": ["User must review this repair plan."],
            "safety_notes": ["This is a proposed repair plan only."],
        },
        "safety_flags": {
            "repair_plan_only": True,
            "repair_applied": False,
            "generated_files_written": False,
            "restore_executed": False,
            "module_rollout_performed": False,
        },
    }


def _not_needed_repair(workflow_run_id):
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": "repair_plan_generator_v73_plan_only",
        "repair_plan_status": "not_needed",
        "repair_plan": {
            "plan_needed": False,
            "repair_kind": "no_repair_needed",
            "failure_category": "none_detected",
            "target_file_candidates": [],
            "proposed_change_summary": "No repair is proposed because no runtime failure signature was detected.",
            "rationale": ["Runtime is currently running."],
            "confidence": 0.9,
            "approval_requirements": [],
            "safety_notes": ["This is a proposed repair plan only."],
        },
        "safety_flags": {
            "repair_plan_only": True,
            "repair_applied": False,
            "generated_files_written": False,
            "restore_executed": False,
            "module_rollout_performed": False,
        },
    }


def _safe(result):
    flags = result.get("safety_flags") or {}
    return (
        flags.get("repair_approval_gate_checked") is True
        and flags.get("approval_required_before_apply") is True
        and flags.get("auto_approval_performed") is False
        and flags.get("generated_files_written") is False
        and flags.get("filesystem_write_performed") is False
        and flags.get("disk_write_performed") is False
        and flags.get("generated_code_execution_performed") is False
        and flags.get("install_packages_performed") is False
        and flags.get("node_command_executed") is False
        and flags.get("python_command_executed") is False
        and flags.get("runtime_server_started") is False
        and flags.get("preview_server_started") is False
        and flags.get("repair_applied") is False
        and flags.get("restore_executed") is False
        and flags.get("module_rollout_performed") is False
    )


def run_check():
    approval_service.reset_repair_approval_records_for_check()
    original_generator = approval_service.generate_repair_plan_for_workflow

    checks = {}
    samples = {}

    try:
        approval_service.generate_repair_plan_for_workflow = _planned_repair
        workflow_run_id = "v74-planned-repair"

        initial_status = approval_service.get_repair_approval_status(workflow_run_id)
        initial_gate = approval_service.assert_repair_apply_allowed(workflow_run_id)
        approved_status = approval_service.approve_repair_plan(
            workflow_run_id=workflow_run_id,
            approved_by="smoke_check",
            approval_note="Approved by V74 smoke check.",
        )
        approved_gate = approval_service.assert_repair_apply_allowed(workflow_run_id)
        rejected_status = approval_service.reject_repair_plan(
            workflow_run_id=workflow_run_id,
            rejected_by="smoke_check",
            rejection_reason="Rejected by V74 smoke check.",
        )
        rejected_gate = approval_service.assert_repair_apply_allowed(workflow_run_id)

        checks["initial_status_not_requested"] = initial_status.get("approval_status") == "not_requested"
        checks["initial_gate_blocked"] = initial_gate.get("apply_allowed") is False and initial_gate.get("blocked") is True
        checks["approval_recorded"] = approved_status.get("approval_status") == "approved" and approved_status.get("approved") is True
        checks["approval_has_metadata"] = (approved_status.get("record") or {}).get("approved_by") == "smoke_check"
        checks["approved_gate_allows"] = approved_gate.get("apply_allowed") is True and approved_gate.get("blocked") is False
        checks["rejection_recorded"] = rejected_status.get("approval_status") == "rejected" and rejected_status.get("approved") is False
        checks["rejection_has_metadata"] = (rejected_status.get("record") or {}).get("rejected_by") == "smoke_check"
        checks["rejected_gate_blocks"] = rejected_gate.get("apply_allowed") is False and rejected_gate.get("blocked") is True
        checks["history_recorded"] = len(rejected_status.get("history") or []) >= 2

        for name, result in {
            "initial_status": initial_status,
            "initial_gate": initial_gate,
            "approved_status": approved_status,
            "approved_gate": approved_gate,
            "rejected_status": rejected_status,
            "rejected_gate": rejected_gate,
        }.items():
            checks[f"{name}_safe"] = _safe(result)
            checks[f"{name}_safety_mode"] = result.get("safety_mode") == approval_service.REPAIR_APPROVAL_GATE_SAFETY_MODE

        approval_service.reset_repair_approval_records_for_check()
        approval_service.generate_repair_plan_for_workflow = _not_needed_repair
        not_needed_workflow_run_id = "v74-not-needed-repair"
        not_needed_status = approval_service.approve_repair_plan(
            workflow_run_id=not_needed_workflow_run_id,
            approved_by="smoke_check",
        )
        not_needed_gate = approval_service.assert_repair_apply_allowed(not_needed_workflow_run_id)

        checks["not_needed_status_recorded"] = not_needed_status.get("approval_status") == "not_needed"
        checks["not_needed_does_not_allow_apply"] = not_needed_gate.get("apply_allowed") is False and not_needed_gate.get("blocked") is True
        checks["not_needed_safe"] = _safe(not_needed_status) and _safe(not_needed_gate)

        samples = {
            "initial_status": initial_status,
            "initial_gate": initial_gate,
            "approved_status": approved_status,
            "approved_gate": approved_gate,
            "rejected_status": rejected_status,
            "rejected_gate": rejected_gate,
            "not_needed_status": not_needed_status,
            "not_needed_gate": not_needed_gate,
        }
    finally:
        approval_service.generate_repair_plan_for_workflow = original_generator
        approval_service.reset_repair_approval_records_for_check()

    return {
        "check": "repair_approval_gate_check",
        "passed": all(checks.values()),
        "checks": checks,
        "sample": samples,
    }


if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
