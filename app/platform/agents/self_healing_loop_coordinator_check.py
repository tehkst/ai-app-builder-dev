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


def _safe(result, *, rerun_attempted_expected):
    flags = result.get("safety_flags") or {}
    return (
        flags.get("self_healing_loop_coordinator_checked") is True
        and flags.get("approval_gates_preserved") is True
        and flags.get("rerun_after_repair_attempted") is rerun_attempted_expected
        and flags.get("auto_approval_performed") is False
        and flags.get("unapproved_repair_applied") is False
        and flags.get("repair_applied_by_loop") is False
        and flags.get("restore_executed") is False
        and flags.get("module_rollout_performed") is False
        and flags.get("install_packages_performed") is False
        and flags.get("python_command_executed") is False
        and flags.get("preview_server_started") is False
    )


def _install_case(*, category="syntax_error", plan_needed=True, approved=False, executed=False, rerun_started=False):
    loop_service.get_controlled_sandbox_runtime_status = _runtime_status
    loop_service.get_controlled_sandbox_runtime_logs = _runtime_logs
    loop_service.analyze_runtime_failure_for_workflow = lambda workflow_run_id: _analysis(category)
    loop_service.generate_repair_plan_for_workflow = lambda workflow_run_id: _repair_plan(plan_needed)
    loop_service.get_repair_approval_status = lambda workflow_run_id: _approval(approved)
    loop_service.get_repair_execution_history = lambda workflow_run_id: _execution_history(executed)
    loop_service.get_repair_rerun_history = lambda workflow_run_id: _rerun_history(rerun_started)


def run_check():
    loop_service.reset_self_healing_loop_history_for_check()

    originals = {
        "status": loop_service.get_controlled_sandbox_runtime_status,
        "logs": loop_service.get_controlled_sandbox_runtime_logs,
        "analysis": loop_service.analyze_runtime_failure_for_workflow,
        "plan": loop_service.generate_repair_plan_for_workflow,
        "approval": loop_service.get_repair_approval_status,
        "execution": loop_service.get_repair_execution_history,
        "rerun_history": loop_service.get_repair_rerun_history,
        "rerun": loop_service.rerun_after_successful_repair,
    }

    checks = {}
    samples = {}
    rerun_calls = []

    try:
        _install_case(category="none_detected", plan_needed=False)
        healthy = loop_service.inspect_self_healing_loop(workflow_run_id=WORKFLOW_RUN_ID)
        checks["healthy_no_repair_needed"] = healthy.get("loop_status") == "healthy_no_repair_needed"
        checks["healthy_safe"] = _safe(healthy, rerun_attempted_expected=False)

        _install_case(category="syntax_error", plan_needed=True, approved=False)
        waiting_approval = loop_service.inspect_self_healing_loop(workflow_run_id=WORKFLOW_RUN_ID)
        checks["waiting_for_repair_approval"] = waiting_approval.get("loop_status") == "waiting_for_repair_approval"
        checks["waiting_approval_safe"] = _safe(waiting_approval, rerun_attempted_expected=False)

        _install_case(category="syntax_error", plan_needed=True, approved=True, executed=False)
        waiting_execution = loop_service.inspect_self_healing_loop(workflow_run_id=WORKFLOW_RUN_ID)
        checks["waiting_for_approved_repair_execution"] = waiting_execution.get("loop_status") == "waiting_for_approved_repair_execution"

        _install_case(category="syntax_error", plan_needed=True, approved=True, executed=True, rerun_started=False)
        waiting_rerun = loop_service.inspect_self_healing_loop(workflow_run_id=WORKFLOW_RUN_ID)
        checks["waiting_for_repair_rerun"] = waiting_rerun.get("loop_status") == "waiting_for_repair_rerun"

        def _tracked_rerun(db, workflow_run_id, requested_by="platform_admin", perform_install=False):
            rerun_calls.append({
                "workflow_run_id": workflow_run_id,
                "requested_by": requested_by,
                "perform_install": perform_install,
            })
            return _rerun_result(db, workflow_run_id, requested_by=requested_by, perform_install=perform_install)

        loop_service.rerun_after_successful_repair = _tracked_rerun

        rerun_history_started = {"value": False}

        def _switching_rerun_history(workflow_run_id):
            return _rerun_history(started=rerun_history_started["value"])

        def _tracked_rerun_and_switch(db, workflow_run_id, requested_by="platform_admin", perform_install=False):
            result = _tracked_rerun(db, workflow_run_id, requested_by=requested_by, perform_install=perform_install)
            rerun_history_started["value"] = True
            return result

        loop_service.get_repair_rerun_history = _switching_rerun_history
        loop_service.rerun_after_successful_repair = _tracked_rerun_and_switch

        run_once = loop_service.run_self_healing_loop_once(
            db=FakeSession(),
            workflow_run_id=WORKFLOW_RUN_ID,
            requested_by="smoke_check",
        )
        checks["run_once_triggers_only_rerun"] = rerun_calls == [
            {"workflow_run_id": WORKFLOW_RUN_ID, "requested_by": "smoke_check", "perform_install": False}
        ]
        checks["run_once_completes_loop"] = run_once.get("loop_status") == "self_healing_loop_completed"
        checks["run_once_history_recorded"] = len(run_once.get("history") or []) == 1
        checks["run_once_safe"] = _safe(run_once, rerun_attempted_expected=True)

        _install_case(category="syntax_error", plan_needed=True, approved=True, executed=True, rerun_started=True)
        completed = loop_service.inspect_self_healing_loop(workflow_run_id=WORKFLOW_RUN_ID)
        checks["completed_rerun_status"] = completed.get("loop_status") == "self_healing_loop_completed"
        checks["completed_safe"] = _safe(completed, rerun_attempted_expected=False)

        history = loop_service.get_self_healing_loop_history(WORKFLOW_RUN_ID)
        checks["history_lookup_has_record"] = len(history.get("history") or []) == 1
        checks["history_lookup_safe"] = _safe(history, rerun_attempted_expected=False)

        samples = {
            "healthy": healthy,
            "waiting_approval": waiting_approval,
            "waiting_execution": waiting_execution,
            "waiting_rerun": waiting_rerun,
            "run_once": run_once,
            "completed": completed,
            "history": history,
        }
    finally:
        loop_service.get_controlled_sandbox_runtime_status = originals["status"]
        loop_service.get_controlled_sandbox_runtime_logs = originals["logs"]
        loop_service.analyze_runtime_failure_for_workflow = originals["analysis"]
        loop_service.generate_repair_plan_for_workflow = originals["plan"]
        loop_service.get_repair_approval_status = originals["approval"]
        loop_service.get_repair_execution_history = originals["execution"]
        loop_service.get_repair_rerun_history = originals["rerun_history"]
        loop_service.rerun_after_successful_repair = originals["rerun"]
        loop_service.reset_self_healing_loop_history_for_check()

    return {
        "check": "self_healing_loop_coordinator_check",
        "passed": all(checks.values()),
        "checks": checks,
        "sample": samples,
    }


if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
