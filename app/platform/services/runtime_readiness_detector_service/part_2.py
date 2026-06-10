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
