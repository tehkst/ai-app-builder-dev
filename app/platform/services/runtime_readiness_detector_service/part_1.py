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
