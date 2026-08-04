from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


V86_DEPLOYMENT_PACK_SAFETY_MODE = "deployment_pack_v86_file_config_check_only"
ROOT = Path(__file__).resolve().parents[3]


REQUIRED_FILES = [
    "Dockerfile",
    ".dockerignore",
    "docs/DEPLOYMENT_PACK_V86.md",
    ".env.example",
]

REQUIRED_ENV_PLACEHOLDERS = [
    "HOSTED_SANDBOX_PROVIDER=local_only",
]


def _safe_flags() -> Dict[str, bool]:
    return {
        "file_config_check_only": True,
        "docker_build_executed": False,
        "docker_container_started": False,
        "kubernetes_started": False,
        "deployment_performed": False,
        "public_url_created": False,
        "database_provisioned": False,
        "secret_written": False,
        "generated_code_execution_performed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "approval_bypass_performed": False,
        "repair_applied": False,
        "restore_executed": False,
        "module_rollout_performed": False,
    }


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _files_exist() -> Dict[str, bool]:
    return {path: (ROOT / path).exists() for path in REQUIRED_FILES}


def _dockerfile_checks(content: str) -> Dict[str, bool]:
    return {
        "uses_python_312_slim": "FROM python:3.12-slim" in content,
        "installs_requirements": "pip install" in content and "requirements.txt" in content,
        "exposes_8000": "EXPOSE 8000" in content,
        "starts_uvicorn": "uvicorn app.main:app" in content,
        "binds_all_interfaces": "--host 0.0.0.0" in content,
        "uses_port_env": "${PORT:-8000}" in content,
    }


def _dockerignore_checks(content: str) -> Dict[str, bool]:
    return {
        "ignores_git": ".git" in content,
        "ignores_env_files": ".env" in content and ".env.*" in content,
        "keeps_env_example": "!.env.example" in content,
        "ignores_virtualenvs": "venv" in content and ".venv" in content,
        "ignores_generated_apps": "generated_apps" in content,
    }


def _env_checks(content: str) -> Dict[str, bool]:
    return {placeholder: placeholder in content for placeholder in REQUIRED_ENV_PLACEHOLDERS}


def _docs_checks(content: str) -> Dict[str, bool]:
    return {
        "mentions_safety_boundary": "Safety Boundary" in content,
        "mentions_no_live_deployment": "does not execute a live deployment" in content,
        "mentions_health_endpoint": "/health" in content,
    }


def _flatten_bool_values(data: Dict[str, Any]) -> List[bool]:
    values: List[bool] = []
    for value in data.values():
        if isinstance(value, dict):
            values.extend(_flatten_bool_values(value))
        elif isinstance(value, bool):
            values.append(value)
    return values


def run_deployment_pack_v86_check() -> Dict[str, Any]:
    files = _files_exist()
    checks: Dict[str, Any] = {"files_exist": files}

    if files.get("Dockerfile"):
        checks["dockerfile"] = _dockerfile_checks(_read("Dockerfile"))
    if files.get(".dockerignore"):
        checks["dockerignore"] = _dockerignore_checks(_read(".dockerignore"))
    if files.get(".env.example"):
        checks["env_example"] = _env_checks(_read(".env.example"))
    if files.get("docs/DEPLOYMENT_PACK_V86.md"):
        checks["deployment_docs"] = _docs_checks(_read("docs/DEPLOYMENT_PACK_V86.md"))

    flags = _safe_flags()
    validation_values = _flatten_bool_values(checks) + [
        flags["file_config_check_only"] is True,
        flags["docker_build_executed"] is False,
        flags["docker_container_started"] is False,
        flags["deployment_performed"] is False,
        flags["public_url_created"] is False,
        flags["secret_written"] is False,
        flags["generated_code_execution_performed"] is False,
    ]
    passed = all(validation_values)

    return {
        "check": "deployment_pack_v86_check",
        "milestone": "V86 — Deployment Preparation (GCP Cloud Run)",
        "passed": passed,
        "safety_mode": V86_DEPLOYMENT_PACK_SAFETY_MODE,
        "checks": checks,
        "safety_flags": flags,
    }


def main() -> int:
    result = run_deployment_pack_v86_check()
    print(result)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
