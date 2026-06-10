# Split from the legacy module to keep each Python file under 200 lines.
import json
import app.platform.services.self_healing_loop_coordinator_service as loop_service
WORKFLOW_RUN_ID = "v77-self-healing-loop"

class FakeSession:
    pass

def _runtime_status(workflow_run_id):
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "exited",
        "safety_mode": "controlled_sandbox_runtime_v70_approved_sandbox_only",
        "safety_flags": {"controlled_sandbox_runtime": True},
    }

def _runtime_logs(workflow_run_id):
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "exited",
        "safety_mode": "controlled_sandbox_runtime_v71_log_capture_only",
        "logs": {
            "stdout_tail": [],
            "stderr_tail": ["SyntaxError: Unexpected token"],
            "stdout_line_count": 0,
            "stderr_line_count": 1,
        },
        "safety_flags": {"runtime_log_capture_enabled": True},
    }

def _analysis(category="syntax_error"):
    return {
        "success": True,
        "found": True,
        "workflow_run_id": WORKFLOW_RUN_ID,
        "safety_mode": "runtime_failure_analyzer_v72_classification_only",
        "analysis_status": "classified",
        "classification": {
            "category": category,
            "severity": "none" if category == "none_detected" else "medium",
            "confidence": 0.9,
            "evidence_lines": [] if category == "none_detected" else ["SyntaxError: Unexpected token"],
            "runtime_status": "running" if category == "none_detected" else "exited",
            "stdout_line_count": 0,
            "stderr_line_count": 0 if category == "none_detected" else 1,
        },
        "safety_flags": {"classification_only": True},
    }

def _repair_plan(plan_needed=True):
    return {
        "success": True,
        "found": True,
        "workflow_run_id": WORKFLOW_RUN_ID,
        "safety_mode": "repair_plan_generator_v73_plan_only",
        "repair_plan_status": "planned" if plan_needed else "not_needed",
        "repair_plan": {
            "plan_needed": plan_needed,
            "repair_kind": "source_code_repair" if plan_needed else "no_repair_needed",
            "failure_category": "syntax_error" if plan_needed else "none_detected",
            "target_file_candidates": ["src/App.jsx"] if plan_needed else [],
            "proposed_change_summary": "Fix syntax error" if plan_needed else "No repair needed",
            "approval_requirements": ["User must approve"] if plan_needed else [],
        },
        "safety_flags": {"repair_plan_only": True, "repair_applied": False},
    }

def _approval(approved=False):
    return {
        "success": True,
        "workflow_run_id": WORKFLOW_RUN_ID,
        "safety_mode": "repair_approval_gate_v74_approval_only",
        "approval_status": "approved" if approved else "not_requested",
        "approved": approved,
        "blocked": not approved,
        "record": {"status": "approved"} if approved else None,
        "history": [],
        "safety_flags": {
            "repair_approval_gate_checked": True,
            "auto_approval_performed": False,
            "repair_applied": False,
        },
    }

def _execution_history(applied=False):
    return {
        "success": True,
        "workflow_run_id": WORKFLOW_RUN_ID,
        "safety_mode": "repair_executor_v75_approval_gated_sandbox_only",
        "history": [
            {
                "workflow_run_id": WORKFLOW_RUN_ID,
                "execution_status": "applied",
                "applied": True,
                "operation_count": 1,
                "created_at": "2026-06-08T00:00:00+00:00",
            }
        ] if applied else [],
        "safety_flags": {"repair_executor_checked": True, "repair_applied": False},
    }

def _rerun_history(started=False):
    return {
        "success": True,
        "workflow_run_id": WORKFLOW_RUN_ID,
        "safety_mode": "repair_rerun_coordinator_v76_after_successful_repair_only",
        "history": [
            {
                "workflow_run_id": WORKFLOW_RUN_ID,
                "rerun_status": "started",
                "rerun_started": True,
                "created_at": "2026-06-08T00:01:00+00:00",
            }
        ] if started else [],
        "safety_flags": {"repair_rerun_coordinator_checked": True},
    }

def _rerun_result(db, workflow_run_id, requested_by="platform_admin", perform_install=False):
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": "repair_rerun_coordinator_v76_after_successful_repair_only",
        "rerun_status": "started",
        "rerun_started": True,
        "blocked": False,
        "safety_flags": {
            "repair_rerun_coordinator_checked": True,
            "auto_approval_performed": False,
            "repair_applied": False,
            "restore_executed": False,
            "module_rollout_performed": False,
            "install_packages_performed": False,
        },
    }
