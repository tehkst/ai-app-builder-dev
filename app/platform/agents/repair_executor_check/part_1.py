# Split from the legacy module to keep each Python file under 200 lines.
import json
import tempfile
from pathlib import Path
import app.platform.services.repair_executor_service as executor_service
WORKFLOW_RUN_ID = "v75-approved-repair"
NOT_NEEDED_WORKFLOW_RUN_ID = "v75-not-needed-repair"
TARGET_RELATIVE_PATH = "src/App.jsx"
ORIGINAL_CONTENT = "export default function App() { return <div>broken</div>; }\n"
REPLACEMENT_CONTENT = "export default function App() { return <div>fixed</div>; }\n"

def _approved_gate(workflow_run_id):
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": "repair_approval_gate_v74_approval_only",
        "apply_allowed": True,
        "blocked": False,
        "block_reason": None,
        "approval_status": "approved",
        "record": {"status": "approved", "workflow_run_id": workflow_run_id},
        "safety_flags": {
            "repair_approval_gate_checked": True,
            "approval_required_before_apply": True,
            "auto_approval_performed": False,
            "repair_applied": False,
            "generated_files_written": False,
            "restore_executed": False,
            "module_rollout_performed": False,
        },
    }

def _blocked_gate(workflow_run_id):
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": "repair_approval_gate_v74_approval_only",
        "apply_allowed": False,
        "blocked": True,
        "block_reason": "Repair application is blocked until the repair plan is explicitly approved.",
        "approval_status": "not_requested",
        "record": None,
        "safety_flags": {
            "repair_approval_gate_checked": True,
            "approval_required_before_apply": True,
            "auto_approval_performed": False,
            "repair_applied": False,
            "generated_files_written": False,
            "restore_executed": False,
            "module_rollout_performed": False,
        },
    }

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
            "target_file_candidates": [TARGET_RELATIVE_PATH],
            "proposed_change_summary": "Replace broken sandbox file content with corrected content.",
            "rationale": ["Synthetic V75 smoke check repair plan."],
            "confidence": 0.9,
            "approval_requirements": ["Repair plan approval must exist."],
            "safety_notes": ["Sandbox-bound replacement only."],
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
            "proposed_change_summary": "No repair required.",
            "rationale": ["No failure detected."],
            "confidence": 0.9,
            "approval_requirements": [],
            "safety_notes": ["No operation should run."],
        },
    }

def _safe(result, *, applied_expected):
    flags = result.get("safety_flags") or {}
    return (
        flags.get("repair_executor_checked") is True
        and flags.get("approval_gate_checked_before_apply") is True
        and flags.get("repair_applied") is applied_expected
        and flags.get("sandbox_bound_repair_only") is True
        and flags.get("auto_approval_performed") is False
        and flags.get("restore_executed") is False
        and flags.get("module_rollout_performed") is False
        and flags.get("generated_code_execution_performed") is False
        and flags.get("install_packages_performed") is False
        and flags.get("node_command_executed") is False
        and flags.get("python_command_executed") is False
        and flags.get("runtime_server_started") is False
        and flags.get("preview_server_started") is False
        and flags.get("process_started") is False
    )
