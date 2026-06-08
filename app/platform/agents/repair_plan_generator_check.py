import json

from app.platform.services.repair_plan_generator_service import generate_repair_plan_from_analysis


def _analysis(
    *,
    workflow_run_id: str,
    category: str,
    evidence_lines=None,
    confidence=0.85,
    exit_code=1,
    runtime_status="exited",
    found=True,
):
    evidence_lines = evidence_lines or []
    return {
        "success": True,
        "found": found,
        "workflow_run_id": workflow_run_id,
        "safety_mode": "runtime_failure_analyzer_v72_classification_only",
        "analysis_status": "classified" if found else "no_logs_found",
        "classification": {
            "category": category,
            "severity": "medium" if category not in {"none_detected", "no_logs_found"} else "none",
            "confidence": confidence,
            "evidence_lines": evidence_lines,
            "exit_code": exit_code,
            "runtime_status": runtime_status,
            "stdout_line_count": 1,
            "stderr_line_count": len(evidence_lines),
        },
        "source_logs": {
            "stdout_tail": [],
            "stderr_tail": evidence_lines,
            "max_lines_per_stream": 200,
        },
        "safety_flags": {
            "runtime_failure_analysis_performed": True,
            "classification_only": True,
            "repair_plan_generated": False,
            "repair_applied": False,
            "restore_executed": False,
            "module_rollout_performed": False,
        },
    }


def _repair_plan(result):
    return result.get("repair_plan") or {}


def _safe(result):
    flags = result.get("safety_flags") or {}
    return (
        flags.get("repair_plan_generated") is True
        and flags.get("repair_plan_only") is True
        and flags.get("approval_required_before_apply") is True
        and flags.get("repair_applied") is False
        and flags.get("generated_files_written") is False
        and flags.get("filesystem_write_performed") is False
        and flags.get("disk_write_performed") is False
        and flags.get("restore_executed") is False
        and flags.get("module_rollout_performed") is False
        and flags.get("generated_code_execution_performed") is False
    )


def run_check():
    cases = {
        "command_not_found": _analysis(
            workflow_run_id="v73-command-not-found",
            category="command_not_found",
            evidence_lines=["sh: vite: command not found"],
            exit_code=127,
        ),
        "missing_dependency": _analysis(
            workflow_run_id="v73-missing-dependency",
            category="missing_dependency",
            evidence_lines=["Error: Cannot find module 'react'"],
        ),
        "syntax_error": _analysis(
            workflow_run_id="v73-syntax-error",
            category="syntax_error",
            evidence_lines=["src/main.jsx:1 SyntaxError: Unexpected token '<'"],
        ),
        "import_error": _analysis(
            workflow_run_id="v73-import-error",
            category="import_error",
            evidence_lines=["ImportError: cannot import name 'Widget' from 'components'"],
        ),
        "port_conflict": _analysis(
            workflow_run_id="v73-port-conflict",
            category="port_conflict",
            evidence_lines=["Error: listen EADDRINUSE: address already in use 127.0.0.1:5173"],
        ),
        "env_var_missing": _analysis(
            workflow_run_id="v73-env-var-missing",
            category="env_var_missing",
            evidence_lines=["Missing environment variable: DATABASE_URL"],
        ),
        "process_exited_early": _analysis(
            workflow_run_id="v73-process-exited-early",
            category="process_exited_early",
            evidence_lines=["Process exited with code 2."],
            exit_code=2,
        ),
        "unknown_runtime_failure": _analysis(
            workflow_run_id="v73-unknown-runtime-failure",
            category="unknown_runtime_failure",
            evidence_lines=["No known failure signature matched the captured runtime logs."],
            confidence=0.35,
        ),
        "none_detected": _analysis(
            workflow_run_id="v73-none-detected",
            category="none_detected",
            evidence_lines=["Runtime is currently running and no known failure signature was detected."],
            confidence=0.9,
            exit_code=None,
            runtime_status="running",
        ),
        "no_logs_found": _analysis(
            workflow_run_id="v73-no-logs-found",
            category="no_logs_found",
            evidence_lines=[],
            confidence=0.0,
            exit_code=None,
            runtime_status="not_started",
            found=False,
        ),
    }

    expected_kinds = {
        "command_not_found": "dependency_or_script_repair",
        "missing_dependency": "dependency_or_script_repair",
        "syntax_error": "source_code_repair",
        "import_error": "source_code_repair",
        "port_conflict": "runtime_configuration_repair",
        "env_var_missing": "configuration_repair",
        "process_exited_early": "manual_review_repair",
        "unknown_runtime_failure": "manual_review_repair",
        "none_detected": "no_repair_needed",
        "no_logs_found": "no_repair_needed",
    }

    results = {name: generate_repair_plan_from_analysis(analysis) for name, analysis in cases.items()}
    checks = {}
    for category, result in results.items():
        plan = _repair_plan(result)
        checks[f"{category}_kind"] = plan.get("repair_kind") == expected_kinds[category]
        checks[f"{category}_safe"] = _safe(result)
        checks[f"{category}_has_summary"] = bool(plan.get("proposed_change_summary"))
        checks[f"{category}_has_safety_notes"] = bool(plan.get("safety_notes"))
        if category in {"none_detected", "no_logs_found"}:
            checks[f"{category}_not_needed"] = result.get("repair_plan_status") == "not_needed" and plan.get("plan_needed") is False
            checks[f"{category}_no_approval_required"] = plan.get("approval_requirements") == []
        else:
            checks[f"{category}_planned"] = result.get("repair_plan_status") == "planned" and plan.get("plan_needed") is True
            checks[f"{category}_approval_required"] = bool(plan.get("approval_requirements"))
            checks[f"{category}_target_candidates"] = bool(plan.get("target_file_candidates"))

    return {
        "check": "repair_plan_generator_check",
        "passed": all(checks.values()),
        "checks": checks,
        "sample": results,
    }


if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
