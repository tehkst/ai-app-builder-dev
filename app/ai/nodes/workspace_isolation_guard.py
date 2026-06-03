from pathlib import PurePosixPath
from typing import Optional, Tuple

from app.ai.state import ProjectState


FORBIDDEN_PLATFORM_PREFIXES = (
    "app/",
    "billing/",
    "auth/",
    "dashboard/",
    "platform/",
    "saas/",
    "tests/",
    ".github/",
)

FORBIDDEN_PATH_PARTS = {
    "..",
    ".git",
    "__pycache__",
}


def is_safe_generated_app_path(file_path: str) -> Tuple[bool, Optional[str]]:
    if not file_path or not isinstance(file_path, str):
        return False, "File path is missing or invalid."

    normalized = file_path.replace("\\", "/").lstrip("/")
    path = PurePosixPath(normalized)

    if path.is_absolute():
        return False, "Absolute paths are not allowed."

    if any(part in FORBIDDEN_PATH_PARTS for part in path.parts):
        return False, "Path traversal or forbidden path part detected."

    if normalized.startswith("generated_apps/"):
        return False, "Manifest paths must be relative to the generated app workspace, not include generated_apps/."

    if normalized.startswith(FORBIDDEN_PLATFORM_PREFIXES):
        return False, "Generated app manifest attempted to target platform code."

    if normalized in {
        "main.py",
        "requirements.txt",
        "Dockerfile",
        "docker-compose.yml",
        ".env.example",
    }:
        return False, "Root-level generated files are not allowed; use backend/ or frontend/."

    allowed_prefixes = (
        "backend/",
        "frontend/",
        "docs/",
    )

    if not normalized.startswith(allowed_prefixes):
        return False, "Generated app files must live under backend/, frontend/, or docs/."

    return True, None


def workspace_isolation_guard_node(state: ProjectState) -> ProjectState:
    manifest = state.get("file_manifest", {})
    files = manifest.get("files", [])

    issues = []

    for file in files:
        file_path = file.get("file_path", "")
        safe, reason = is_safe_generated_app_path(file_path)

        if not safe:
            issues.append(
                {
                    "severity": "critical",
                    "file_path": file_path,
                    "issue": reason,
                }
            )

    passed = len(issues) == 0

    return {
        **state,
        "workspace_isolation_report": {
            "passed": passed,
            "issues": issues,
            "rule": "Generated app manifests may only target files inside the customer generated app workspace. Platform code must remain immutable during customer app generation.",
        },
        "current_step": "workspace_isolation_passed" if passed else "workspace_isolation_failed",
    }
