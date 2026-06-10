# Split from the legacy module to keep each Python file under 200 lines.
import json
import re
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.platform.persistence.models import PlatformGeneratedFile
NODE_MANAGERS = {
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
}
PYTHON_ENTRY_NAMES = {"app.py", "main.py", "server.py", "run.py"}
NODE_ENTRY_NAMES = {"server.js", "app.js", "index.js", "main.js"}

def detect_runtime_readiness_for_generated_file(
    db: Session,
    generated_file_id: str,
) -> Dict[str, Any]:
    selected = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.generated_file_id == generated_file_id)
        .first()
    )

    if not selected:
        return {
            "success": False,
            "found": False,
            "generated_file_id": generated_file_id,
            "runtime_readiness": None,
            "safety_flags": _safety_flags(),
            "safety_mode": "runtime_readiness_detection_only_no_execution",
        }

    files = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.workflow_run_id == selected.workflow_run_id)
        .order_by(PlatformGeneratedFile.path.asc())
        .all()
    )

    return detect_runtime_readiness_from_files(
        files=files,
        workflow_run_id=selected.workflow_run_id,
        selected_generated_file_id=generated_file_id,
    )

def detect_runtime_readiness_from_files(
    files: List[PlatformGeneratedFile],
    workflow_run_id: str,
    selected_generated_file_id: Optional[str] = None,
) -> Dict[str, Any]:
    files_by_name = {_basename(file.path): file for file in files}

    package_json = _package_json(files_by_name)
    has_python = any(
        _basename(file.path).endswith(".py") or (file.language or "").lower() == "python"
        for file in files
    )

    framework_type = _detect_framework(
        files=files,
        files_by_name=files_by_name,
        package_json=package_json,
    )
    entries = _entry_files(files)
    package_manager = _detect_package_manager(files_by_name, package_json, has_python)
    port_hints = _extract_port_hints(files)
    env_hints = _extract_env_hints(files)

    likely_install_command = _likely_install_command(package_manager, files_by_name)
    likely_run_command = _likely_run_command(
        framework_type=framework_type,
        package_manager=package_manager,
        package_json=package_json,
        entries=entries,
    )

    likely_port = _likely_port(framework_type, port_hints)

    approval_requirements = []
    if likely_install_command:
        approval_requirements.append("package_install_approval_required_before_future_install")
    if likely_run_command:
        approval_requirements.append("runtime_start_approval_required_before_future_run")
    if framework_type != "static_html":
        approval_requirements.append("sandbox_execution_approval_required_before_future_execution")
    if not approval_requirements:
        approval_requirements.append("manual_review_required_before_future_runtime_action")

    readiness_status = "not_ready"
    if framework_type == "static_html" and entries:
        readiness_status = "static_preview_ready"
    elif likely_run_command:
        readiness_status = "runtime_plan_detected"
    elif framework_type != "unknown":
        readiness_status = "partial_runtime_plan_detected"

    return {
        "success": True,
        "found": bool(files),
        "workflow_run_id": workflow_run_id,
        "selected_generated_file_id": selected_generated_file_id,
        "runtime_readiness": {
            "status": readiness_status,
            "framework_type": framework_type,
            "entry_files": entries,
            "package_manager": package_manager,
            "likely_install_command": likely_install_command,
            "likely_run_command": likely_run_command,
            "likely_port": likely_port,
            "port_hints": port_hints,
            "env_var_hints": env_hints,
            "approval_requirements": approval_requirements,
            "generated_file_count": len(files),
            "inspected_files": [
                {
                    "generated_file_id": file.generated_file_id,
                    "path": _normalise_path(file.path),
                    "language": file.language,
                    "write_status": file.write_status,
                }
                for file in files
            ],
        },
        "safety_flags": _safety_flags(),
        "safety_mode": "runtime_readiness_detection_only_no_execution",
    }
