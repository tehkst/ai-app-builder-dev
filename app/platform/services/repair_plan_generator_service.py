from __future__ import annotations

from typing import Any, Dict, List

from app.platform.services.runtime_failure_analyzer_service import analyze_runtime_failure_for_workflow


REPAIR_PLAN_GENERATOR_SAFETY_MODE = "repair_plan_generator_v73_plan_only"


def _safe_flags() -> Dict[str, bool]:
    return {
        "repair_plan_generated": True,
        "repair_plan_only": True,
        "approval_required_before_apply": True,
        "runtime_failure_analysis_required": True,
        "generated_files_written": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "generated_code_execution_performed": False,
        "install_packages_performed": False,
        "node_command_executed": False,
        "python_command_executed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "repair_applied": False,
        "restore_executed": False,
        "module_rollout_performed": False,
    }


def _target_file_candidates(category: str, evidence_lines: List[str]) -> List[str]:
    evidence = "\n".join(evidence_lines).lower()
    if category in {"command_not_found", "missing_dependency"}:
        return ["package.json"]
    if category in {"syntax_error", "import_error"}:
        candidates = []
        for line in evidence_lines:
            for token in line.replace("(", " ").replace(")", " ").replace(":", " ").split():
                if token.endswith((".js", ".jsx", ".ts", ".tsx", ".py")):
                    candidates.append(token)
        return candidates or ["src/main.jsx", "src/App.jsx", "generated source file"]
    if category == "env_var_missing":
        return [".env.example", "runtime configuration", "generated source file using environment variables"]
    if category == "port_conflict":
        return ["runtime run plan", "package.json", "dev server configuration"]
    if category in {"process_exited_early", "unknown_runtime_failure"}:
        return ["runtime entry file", "package.json", "generated source files"]
    return []


def _change_summary(category: str) -> str:
    summaries = {
        "command_not_found": "Review package scripts and dependency declarations so the approved run command can resolve its executable.",
        "missing_dependency": "Add or correct the missing dependency declaration and ensure imports match installed package names.",
        "syntax_error": "Inspect the referenced generated source file and correct the syntax near the evidence line.",
        "import_error": "Fix the import path, exported symbol name, or source file structure referenced by the runtime error.",
        "port_conflict": "Adjust the approved runtime port or dev server configuration to avoid the occupied port.",
        "env_var_missing": "Document or provide the missing environment variable through approved configuration before rerun.",
        "process_exited_early": "Inspect startup entrypoints and package scripts to identify why the process exited before remaining healthy.",
        "unknown_runtime_failure": "Review captured stdout/stderr manually and prepare a targeted repair after the failure is better understood.",
        "none_detected": "No repair is proposed because no runtime failure signature was detected.",
        "no_logs_found": "No repair is proposed because no runtime logs are available for analysis.",
    }
    return summaries.get(category, "Review runtime evidence and prepare a targeted repair plan before applying any changes.")


def _repair_kind(category: str) -> str:
    if category in {"command_not_found", "missing_dependency"}:
        return "dependency_or_script_repair"
    if category in {"syntax_error", "import_error"}:
        return "source_code_repair"
    if category == "env_var_missing":
        return "configuration_repair"
    if category == "port_conflict":
        return "runtime_configuration_repair"
    if category in {"process_exited_early", "unknown_runtime_failure"}:
        return "manual_review_repair"
    return "no_repair_needed"


def _approval_requirements(category: str) -> List[str]:
    if category in {"none_detected", "no_logs_found"}:
        return []
    return [
        "User must review this repair plan.",
        "User must approve exact file changes in a later milestone before any repair is applied.",
        "Repair application must remain sandbox-bound and approval-gated.",
    ]


def _confidence(classification: Dict[str, Any]) -> float:
    base = float(classification.get("confidence") or 0.0)
    category = classification.get("category")
    if category in {"none_detected", "no_logs_found"}:
        return base
    return min(0.95, max(0.25, base - 0.1))


def generate_repair_plan_from_analysis(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    classification = analysis_result.get("classification") or {}
    category = str(classification.get("category") or "unknown_runtime_failure")
    evidence_lines = [str(line) for line in (classification.get("evidence_lines") or [])]
    plan_needed = category not in {"none_detected", "no_logs_found"}

    repair_plan = {
        "plan_needed": plan_needed,
        "repair_kind": _repair_kind(category),
        "failure_category": category,
        "target_file_candidates": _target_file_candidates(category, evidence_lines),
        "proposed_change_summary": _change_summary(category),
        "rationale": evidence_lines or ["No evidence lines were available; manual review is required before any repair."],
        "confidence": _confidence(classification),
        "approval_requirements": _approval_requirements(category),
        "safety_notes": [
            "This is a proposed repair plan only.",
            "No generated files were modified.",
            "No repair was applied.",
            "No restore or rollout was executed.",
        ],
    }

    return {
        "success": True,
        "found": bool(analysis_result.get("found")),
        "workflow_run_id": analysis_result.get("workflow_run_id"),
        "safety_mode": REPAIR_PLAN_GENERATOR_SAFETY_MODE,
        "repair_plan_status": "planned" if plan_needed else "not_needed",
        "source_analysis": {
            "analysis_status": analysis_result.get("analysis_status"),
            "classification": classification,
            "safety_mode": analysis_result.get("safety_mode"),
        },
        "repair_plan": repair_plan,
        "safety_flags": _safe_flags(),
    }


def generate_repair_plan_for_workflow(workflow_run_id: str) -> Dict[str, Any]:
    analysis_result = analyze_runtime_failure_for_workflow(workflow_run_id)
    return generate_repair_plan_from_analysis(analysis_result)
