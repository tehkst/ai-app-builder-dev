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


def _normalise_path(path: str) -> str:
    return str(PurePosixPath(path or "").as_posix()).lstrip("./")


def _basename(path: str) -> str:
    return PurePosixPath(_normalise_path(path)).name


def _safe_json_loads(raw: str) -> Dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _content_contains(content: str, patterns: List[str]) -> bool:
    lowered = (content or "").lower()
    return any(pattern.lower() in lowered for pattern in patterns)


def _extract_port_hints(files: List[PlatformGeneratedFile]) -> List[int]:
    ports = set()
    for file in files:
        content = file.content_preview or ""
        for match in re.findall(r"(?:PORT|port)\D{0,20}([1-9][0-9]{2,5})", content):
            port = int(match)
            if 1 <= port <= 65535:
                ports.add(port)
        for match in re.findall(r"listen\(\s*([1-9][0-9]{2,5})", content):
            port = int(match)
            if 1 <= port <= 65535:
                ports.add(port)
    return sorted(ports)


def _extract_env_hints(files: List[PlatformGeneratedFile]) -> List[str]:
    hints = set()
    patterns = [
        re.compile(r"\bprocess\.env\.([A-Z][A-Z0-9_]{1,80})"),
        re.compile(r"\bimport\.meta\.env\.([A-Z][A-Z0-9_]{1,80})"),
        re.compile(r"\bos\.environ\.get\(['\"]([A-Z][A-Z0-9_]{1,80})"),
        re.compile(r"\bos\.getenv\(['\"]([A-Z][A-Z0-9_]{1,80})"),
    ]

    for file in files:
        content = file.content_preview or ""
        for pattern in patterns:
            for match in pattern.findall(content):
                hints.add(match)

    return sorted(hints)


def _package_json(files_by_name: Dict[str, PlatformGeneratedFile]) -> Dict[str, Any]:
    package_file = files_by_name.get("package.json")
    if not package_file:
        return {}
    return _safe_json_loads(package_file.content_preview)


def _detect_package_manager(
    files_by_name: Dict[str, PlatformGeneratedFile],
    package_json: Dict[str, Any],
    has_python: bool,
) -> str:
    for lock_file, manager in NODE_MANAGERS.items():
        if lock_file in files_by_name:
            return manager
    if package_json:
        return "npm"
    if has_python:
        if "requirements.txt" in files_by_name or "pyproject.toml" in files_by_name:
            return "pip"
        return "python"
    return "none"


def _node_run_command(manager: str, package_json: Dict[str, Any]) -> Optional[str]:
    scripts = package_json.get("scripts") if isinstance(package_json.get("scripts"), dict) else {}
    runner = {
        "npm": "npm run",
        "yarn": "yarn",
        "pnpm": "pnpm",
    }.get(manager, "npm run")

    if "dev" in scripts:
        return f"{runner} dev"
    if "start" in scripts:
        return f"{runner} start"
    if "serve" in scripts:
        return f"{runner} serve"
    return None


def _detect_framework(
    files: List[PlatformGeneratedFile],
    files_by_name: Dict[str, PlatformGeneratedFile],
    package_json: Dict[str, Any],
) -> str:
    package_blob = json.dumps(package_json).lower()

    if "next" in package_blob or "next.config.js" in files_by_name or "next.config.mjs" in files_by_name:
        return "nextjs"

    if "vite" in package_blob or "vite.config.js" in files_by_name or "vite.config.ts" in files_by_name:
        return "vite_react"

    if "react" in package_blob:
        return "react"

    for file in files:
        name = _basename(file.path)
        content = file.content_preview or ""

        if name in NODE_ENTRY_NAMES and _content_contains(
            content,
            ["express(", "from 'express'", 'from "express"', "require('express')", 'require("express")'],
        ):
            return "express"

        if name in PYTHON_ENTRY_NAMES and _content_contains(content, ["fastapi", "uvicorn"]):
            return "fastapi"

        if name in PYTHON_ENTRY_NAMES and _content_contains(content, ["flask", "app.run("]):
            return "flask"

    if "index.html" in files_by_name and not package_json:
        return "static_html"

    if any(_basename(file.path) in PYTHON_ENTRY_NAMES for file in files):
        return "python_script"

    return "unknown"


def _entry_files(files: List[PlatformGeneratedFile]) -> List[str]:
    interesting_names = {
        "package.json",
        "index.html",
        "app.py",
        "main.py",
        "server.py",
        "server.js",
        "app.js",
        "index.js",
        "main.js",
        "vite.config.js",
        "vite.config.ts",
        "next.config.js",
        "next.config.mjs",
        "requirements.txt",
        "pyproject.toml",
    }

    entries = []
    for file in files:
        path = _normalise_path(file.path)
        if _basename(path) in interesting_names:
            entries.append(path)

    return sorted(set(entries))


def _likely_install_command(package_manager: str, files_by_name: Dict[str, PlatformGeneratedFile]) -> Optional[str]:
    if package_manager == "npm":
        return "npm install"
    if package_manager == "yarn":
        return "yarn install"
    if package_manager == "pnpm":
        return "pnpm install"
    if package_manager == "pip":
        if "requirements.txt" in files_by_name:
            return "pip install -r requirements.txt"
        if "pyproject.toml" in files_by_name:
            return "pip install -e ."
    return None


def _likely_run_command(
    framework_type: str,
    package_manager: str,
    package_json: Dict[str, Any],
    entries: List[str],
) -> Optional[str]:
    if framework_type in {"vite_react", "react", "nextjs", "express"}:
        command = _node_run_command(package_manager, package_json)
        if command:
            return command

    if framework_type == "nextjs":
        return "npm run dev"

    if framework_type in {"vite_react", "react"}:
        return "npm run dev"

    if framework_type == "express":
        for entry in entries:
            if _basename(entry) in NODE_ENTRY_NAMES:
                return f"node {entry}"
        return "node server.js"

    if framework_type == "fastapi":
        for entry in entries:
            if _basename(entry) in {"main.py", "app.py"}:
                module = entry[:-3].replace("/", ".")
                return f"uvicorn {module}:app --reload"
        return "uvicorn main:app --reload"

    if framework_type == "flask":
        for entry in entries:
            if _basename(entry) in {"app.py", "main.py"}:
                return f"python {entry}"
        return "flask run"

    if framework_type == "python_script":
        for entry in entries:
            if _basename(entry) in PYTHON_ENTRY_NAMES:
                return f"python {entry}"

    return None


def _likely_port(framework_type: str, port_hints: List[int]) -> Optional[int]:
    if port_hints:
        return port_hints[0]
    defaults = {
        "vite_react": 5173,
        "react": 3000,
        "nextjs": 3000,
        "express": 3000,
        "fastapi": 8000,
        "flask": 5000,
    }
    return defaults.get(framework_type)


def _safety_flags() -> Dict[str, bool]:
    return {
        "detection_only": True,
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
        "repair_applied": False,
        "restore_executed": False,
    }


def detect_runtime_readiness_for_workflow(
    db: Session,
    workflow_run_id: str,
) -> Dict[str, Any]:
    files = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.workflow_run_id == workflow_run_id)
        .order_by(PlatformGeneratedFile.path.asc())
        .all()
    )

    return detect_runtime_readiness_from_files(
        files=files,
        workflow_run_id=workflow_run_id,
    )


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
