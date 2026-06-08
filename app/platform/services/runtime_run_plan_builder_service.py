from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.services.runtime_readiness_detector_service import (
    detect_runtime_readiness_for_generated_file,
    detect_runtime_readiness_for_workflow,
)


RUNTIME_RUN_PLAN_SAFETY_MODE = "runtime_run_plan_builder_only_no_execution"


def _normalise_path(path: Optional[str]) -> str:
    return str(PurePosixPath(path or "").as_posix()).lstrip("./")


def _working_directory_from_entry_files(entry_files: List[str]) -> str:
    if not entry_files:
        return "."

    preferred_names = {
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "vite.config.js",
        "vite.config.ts",
        "next.config.js",
        "next.config.mjs",
        "main.py",
        "app.py",
        "server.py",
        "index.html",
    }

    for entry in entry_files:
        path = PurePosixPath(_normalise_path(entry))
        if path.name in preferred_names:
            parent = str(path.parent)
            return "." if parent == "." else parent

    path = PurePosixPath(_normalise_path(entry_files[0]))
    parent = str(path.parent)
    return "." if parent == "." else parent


def _command_requires_install(command: Optional[str]) -> bool:
    return bool(command and command.strip())


def _command_requires_runtime(command: Optional[str]) -> bool:
    return bool(command and command.strip())


def _build_blocking_reasons(readiness: Dict[str, Any]) -> List[str]:
    reasons = []

    if not readiness:
        return ["runtime_readiness_missing"]

    framework_type = readiness.get("framework_type")
    status = readiness.get("status")
    likely_run_command = readiness.get("likely_run_command")
    entry_files = readiness.get("entry_files") or []

    if not framework_type or framework_type == "unknown":
        reasons.append("unknown_framework_type")

    if status == "not_ready":
        reasons.append("readiness_status_not_ready")

    if framework_type != "static_html" and not likely_run_command:
        reasons.append("missing_runtime_run_command")

    if not entry_files:
        reasons.append("missing_entry_files")

    return reasons


def _approval_requirements(readiness: Dict[str, Any]) -> List[str]:
    requirements = list(readiness.get("approval_requirements") or [])
    if "runtime_run_plan_review_required" not in requirements:
        requirements.insert(0, "runtime_run_plan_review_required")
    return requirements


def _safety_flags() -> Dict[str, bool]:
    return {
        "plan_only": True,
        "detection_only": False,
        "install_packages_performed": False,
        "npm_install_performed": False,
        "pip_install_performed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "server_start_performed": False,
        "generated_code_execution_performed": False,
        "node_command_executed": False,
        "python_command_executed": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "generated_files_written": False,
        "repair_applied": False,
        "restore_executed": False,
    }


def build_runtime_run_plan_from_readiness(
    readiness_result: Dict[str, Any],
) -> Dict[str, Any]:
    readiness = readiness_result.get("runtime_readiness") or {}
    blocking_reasons = _build_blocking_reasons(readiness)
    entry_files = readiness.get("entry_files") or []
    working_directory = _working_directory_from_entry_files(entry_files)

    likely_install_command = readiness.get("likely_install_command")
    likely_run_command = readiness.get("likely_run_command")
    likely_port = readiness.get("likely_port")
    framework_type = readiness.get("framework_type")

    install_step = {
        "required": _command_requires_install(likely_install_command),
        "command": likely_install_command,
        "working_directory": working_directory,
        "approval_required": _command_requires_install(likely_install_command),
        "performed": False,
    }

    run_step = {
        "required": _command_requires_runtime(likely_run_command),
        "command": likely_run_command,
        "working_directory": working_directory,
        "port": likely_port,
        "approval_required": _command_requires_runtime(likely_run_command),
        "performed": False,
    }

    runtime_plan_status = "blocked"
    if not blocking_reasons and framework_type == "static_html":
        runtime_plan_status = "static_manual_preview_plan_ready"
    elif not blocking_reasons:
        runtime_plan_status = "runtime_run_plan_ready_for_approval"

    return {
        "success": readiness_result.get("success") is True,
        "found": readiness_result.get("found") is True,
        "workflow_run_id": readiness_result.get("workflow_run_id"),
        "selected_generated_file_id": readiness_result.get("selected_generated_file_id"),
        "runtime_run_plan": {
            "status": runtime_plan_status,
            "framework_type": framework_type,
            "working_directory": working_directory,
            "entry_files": entry_files,
            "package_manager": readiness.get("package_manager"),
            "install_step": install_step,
            "run_step": run_step,
            "port": likely_port,
            "env_requirements": readiness.get("env_var_hints") or [],
            "approval_requirements": _approval_requirements(readiness),
            "blocking_reasons": blocking_reasons,
            "source_readiness_status": readiness.get("status"),
            "source_generated_file_count": readiness.get("generated_file_count"),
        },
        "source_runtime_readiness": readiness_result,
        "safety_flags": _safety_flags(),
        "safety_mode": RUNTIME_RUN_PLAN_SAFETY_MODE,
    }


def build_runtime_run_plan_for_workflow(
    db: Session,
    workflow_run_id: str,
) -> Dict[str, Any]:
    readiness_result = detect_runtime_readiness_for_workflow(
        db,
        workflow_run_id=workflow_run_id,
    )
    return build_runtime_run_plan_from_readiness(readiness_result)


def build_runtime_run_plan_for_generated_file(
    db: Session,
    generated_file_id: str,
) -> Dict[str, Any]:
    readiness_result = detect_runtime_readiness_for_generated_file(
        db,
        generated_file_id=generated_file_id,
    )
    return build_runtime_run_plan_from_readiness(readiness_result)
