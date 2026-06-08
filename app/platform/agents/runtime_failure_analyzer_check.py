import json

from app.platform.services.runtime_failure_analyzer_service import analyze_runtime_failure_from_logs


def _snapshot(
    *,
    workflow_run_id: str,
    stdout_tail=None,
    stderr_tail=None,
    exit_code=None,
    runtime_status="exited",
):
    stdout_tail = stdout_tail or []
    stderr_tail = stderr_tail or []
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "runtime_status": runtime_status,
        "process": {
            "pid": 12345,
            "poll": exit_code,
            "running": runtime_status == "running",
            "exit_code": exit_code,
            "command": "npm run dev",
            "argv": ["npm", "run", "dev", "--", "--host", "127.0.0.1"],
        },
        "logs": {
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
            "stdout_line_count": len(stdout_tail),
            "stderr_line_count": len(stderr_tail),
            "max_lines_per_stream": 200,
            "readers_started": True,
            "readers_completed": runtime_status != "running",
        },
        "safety_mode": "controlled_sandbox_runtime_v71_log_capture_only",
        "safety_flags": {
            "runtime_log_capture_enabled": True,
            "repair_plan_generated": False,
            "repair_applied": False,
            "restore_executed": False,
            "module_rollout_performed": False,
        },
    }


def _category(result):
    return (result.get("classification") or {}).get("category")


def _safe(result):
    flags = result.get("safety_flags") or {}
    return (
        flags.get("classification_only") is True
        and flags.get("repair_plan_generated") is False
        and flags.get("repair_applied") is False
        and flags.get("restore_executed") is False
        and flags.get("module_rollout_performed") is False
        and flags.get("generated_code_execution_performed") is False
        and flags.get("filesystem_write_performed") is False
        and flags.get("disk_write_performed") is False
    )


def run_check():
    cases = {
        "command_not_found": _snapshot(
            workflow_run_id="v72-command-not-found",
            stdout_tail=["> dev", "> vite --host 127.0.0.1"],
            stderr_tail=["sh: vite: command not found"],
            exit_code=127,
        ),
        "missing_dependency": _snapshot(
            workflow_run_id="v72-missing-dependency",
            stderr_tail=["Error: Cannot find module 'react'"],
            exit_code=1,
        ),
        "syntax_error": _snapshot(
            workflow_run_id="v72-syntax-error",
            stderr_tail=["SyntaxError: Unexpected token '<'"],
            exit_code=1,
        ),
        "import_error": _snapshot(
            workflow_run_id="v72-import-error",
            stderr_tail=["ImportError: cannot import name 'Widget' from 'components'"],
            exit_code=1,
        ),
        "port_conflict": _snapshot(
            workflow_run_id="v72-port-conflict",
            stderr_tail=["Error: listen EADDRINUSE: address already in use 127.0.0.1:5173"],
            exit_code=1,
        ),
        "env_var_missing": _snapshot(
            workflow_run_id="v72-env-var-missing",
            stderr_tail=["Missing environment variable: DATABASE_URL"],
            exit_code=1,
        ),
        "process_exited_early": _snapshot(
            workflow_run_id="v72-process-exited-early",
            stdout_tail=["Starting app"],
            stderr_tail=[],
            exit_code=2,
        ),
        "none_detected": _snapshot(
            workflow_run_id="v72-none-detected",
            stdout_tail=["VITE ready in 200 ms", "Local: http://127.0.0.1:5173"],
            stderr_tail=[],
            exit_code=None,
            runtime_status="running",
        ),
    }

    results = {name: analyze_runtime_failure_from_logs(snapshot) for name, snapshot in cases.items()}
    checks = {}
    for expected_category, result in results.items():
        checks[f"{expected_category}_classified"] = _category(result) == expected_category
        checks[f"{expected_category}_has_evidence"] = bool((result.get("classification") or {}).get("evidence_lines"))
        checks[f"{expected_category}_safe"] = _safe(result)

    no_logs_result = analyze_runtime_failure_from_logs(
        {
            "success": True,
            "found": False,
            "workflow_run_id": "v72-no-logs",
            "runtime_status": "not_started",
            "process": None,
            "logs": {"stdout_tail": [], "stderr_tail": [], "stdout_line_count": 0, "stderr_line_count": 0},
        }
    )
    checks["no_logs_found"] = _category(no_logs_result) == "no_logs_found"
    checks["no_logs_safe"] = _safe(no_logs_result)

    return {
        "check": "runtime_failure_analyzer_check",
        "passed": all(checks.values()),
        "checks": checks,
        "sample": {
            "results": results,
            "no_logs_result": no_logs_result,
        },
    }


if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
