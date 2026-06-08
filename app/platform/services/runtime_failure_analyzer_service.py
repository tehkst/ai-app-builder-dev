from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.platform.services.controlled_sandbox_runtime_service import get_controlled_sandbox_runtime_logs


RUNTIME_FAILURE_ANALYZER_SAFETY_MODE = "runtime_failure_analyzer_v72_classification_only"


def _safe_flags() -> Dict[str, bool]:
    return {
        "runtime_failure_analysis_performed": True,
        "classification_only": True,
        "runtime_log_capture_required": True,
        "generated_files_written": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "generated_code_execution_performed": False,
        "install_packages_performed": False,
        "node_command_executed": False,
        "python_command_executed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "repair_plan_generated": False,
        "repair_applied": False,
        "restore_executed": False,
        "module_rollout_performed": False,
    }


def _line_matches(lines: List[str], *needles: str) -> Optional[str]:
    lowered_needles = [needle.lower() for needle in needles]
    for line in lines:
        lowered = line.lower()
        if any(needle in lowered for needle in lowered_needles):
            return line
    return None


def _combined_lines(log_snapshot: Dict[str, Any]) -> Tuple[List[str], List[str], List[str]]:
    logs = log_snapshot.get("logs") or {}
    stdout_lines = [str(line) for line in (logs.get("stdout_tail") or [])]
    stderr_lines = [str(line) for line in (logs.get("stderr_tail") or [])]
    return stdout_lines, stderr_lines, stdout_lines + stderr_lines


def _severity_for(category: str) -> str:
    if category in {"none_detected"}:
        return "none"
    if category in {"unknown_runtime_failure", "startup_timeout", "process_exited_early"}:
        return "high"
    return "medium"


def _confidence_for(category: str, evidence: List[str]) -> float:
    if category == "none_detected":
        return 0.9
    if category == "unknown_runtime_failure":
        return 0.35 if evidence else 0.2
    return 0.85 if evidence else 0.55


def _classify_from_lines(lines: List[str], exit_code: Optional[int], runtime_status: str) -> Tuple[str, List[str]]:
    checks = [
        ("command_not_found", ("command not found", "not found", "is not recognized as", "sh: vite: command not found")),
        ("missing_dependency", ("cannot find package", "could not resolve dependency", "module not found", "cannot find module", "can't resolve")),
        ("import_error", ("importerror", "cannot import", "failed to resolve import", "does not provide an export")),
        ("syntax_error", ("syntaxerror", "unexpected token", "unexpected identifier", "unterminated string")),
        ("port_conflict", ("eaddrinuse", "address already in use", "port is already in use")),
        ("env_var_missing", ("environment variable", "missing env", "missing environment", "process.env", "env var")),
        ("startup_timeout", ("startup timeout", "timed out", "timeout waiting")),
    ]
    for category, needles in checks:
        evidence = _line_matches(lines, *needles)
        if evidence:
            return category, [evidence]

    if exit_code not in (None, 0):
        return "process_exited_early", [f"Process exited with code {exit_code}."]
    if runtime_status in {"exited", "exited_early"}:
        return "process_exited_early", [f"Runtime status is {runtime_status}."]
    if runtime_status == "running":
        return "none_detected", ["Runtime is currently running and no known failure signature was detected."]
    return "unknown_runtime_failure", ["No known failure signature matched the captured runtime logs."]


def analyze_runtime_failure_from_logs(log_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    stdout_lines, stderr_lines, all_lines = _combined_lines(log_snapshot)
    process = log_snapshot.get("process") or {}
    exit_code = process.get("exit_code") if process.get("exit_code") is not None else process.get("poll")
    runtime_status = str(log_snapshot.get("runtime_status") or "unknown")
    category, evidence = _classify_from_lines(all_lines, exit_code, runtime_status)
    severity = _severity_for(category)
    confidence = _confidence_for(category, evidence)

    return {
        "success": True,
        "found": bool(log_snapshot.get("found")),
        "workflow_run_id": log_snapshot.get("workflow_run_id"),
        "safety_mode": RUNTIME_FAILURE_ANALYZER_SAFETY_MODE,
        "analysis_status": "classified" if log_snapshot.get("found") else "no_logs_found",
        "classification": {
            "category": category if log_snapshot.get("found") else "no_logs_found",
            "severity": severity if log_snapshot.get("found") else "none",
            "confidence": confidence if log_snapshot.get("found") else 0.0,
            "evidence_lines": evidence if log_snapshot.get("found") else [],
            "exit_code": exit_code,
            "runtime_status": runtime_status,
            "stdout_line_count": (log_snapshot.get("logs") or {}).get("stdout_line_count") or 0,
            "stderr_line_count": (log_snapshot.get("logs") or {}).get("stderr_line_count") or 0,
        },
        "source_logs": {
            "stdout_tail": stdout_lines,
            "stderr_tail": stderr_lines,
            "max_lines_per_stream": (log_snapshot.get("logs") or {}).get("max_lines_per_stream"),
        },
        "safety_flags": _safe_flags(),
    }


def analyze_runtime_failure_for_workflow(workflow_run_id: str) -> Dict[str, Any]:
    log_snapshot = get_controlled_sandbox_runtime_logs(workflow_run_id)
    return analyze_runtime_failure_from_logs(log_snapshot)
