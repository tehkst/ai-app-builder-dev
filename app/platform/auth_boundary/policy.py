from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

AUTH_BOUNDARY_FILES = {
    "app/platform/auth/service.py",
    "app/platform/auth/auth_check.py",
    "app/platform/auth/login_boundary_check.py",
    "app/platform/ui/auth_safe_dashboard.py",
    "app/platform/ui/landing.py",
}

AUTH_BOUNDARY_PREFIXES = (
    "app/platform/auth/",
)

AUTH_SHELL_FILES = {
    "app/platform/ui/founder_dashboard_stable.py",
    "app/platform/ui/mission_control.py",
}

AUTH_MISSION_TYPES = {
    "auth",
    "authentication",
    "security-auth",
    "login-boundary",
    "session-management",
}


def build_auth_boundary_policy() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Auth Boundary Protection Rule",
        "milestone": "PROTECT-01",
        "status": "auth-boundary-policy-ready",
        "purpose": "Prevent non-auth missions from modifying login, authentication, session, or auth-shell files.",
        "protected_files": sorted(AUTH_BOUNDARY_FILES | AUTH_SHELL_FILES),
        "protected_prefixes": list(AUTH_BOUNDARY_PREFIXES),
        "allowed_mission_types": sorted(AUTH_MISSION_TYPES),
        "rule": "Any proposed change touching protected auth boundary files must declare an authentication mission type and carry explicit founder approval.",
    }


def validate_auth_boundary(payload: dict[str, Any]) -> dict[str, Any]:
    mission_type = str(payload.get("mission_type") or payload.get("type") or "").strip().lower()
    approval = payload.get("approval") if isinstance(payload.get("approval"), dict) else {}
    approved = str(payload.get("approval_status") or approval.get("status") or "").strip().lower() == "approved"
    files = _extract_files(payload)
    protected = [path for path in files if is_auth_boundary_path(path)]
    allowed = bool(protected) is False or (mission_type in AUTH_MISSION_TYPES and approved)
    return {
        "company": "AI Software Factory",
        "product": "Auth Boundary Protection Rule",
        "milestone": "PROTECT-01",
        "status": "auth-boundary-pass" if allowed else "blocked-auth-boundary-change",
        "mission_type": mission_type or "unspecified",
        "founder_approval_present": approved,
        "files_checked": files,
        "protected_files_touched": protected,
        "allowed": allowed,
        "reason": "No protected auth files touched."
        if not protected
        else "Protected auth files require authentication mission type and founder approval.",
    }


def is_auth_boundary_path(path: str) -> bool:
    normalized = _normalize_path(path)
    if normalized in AUTH_BOUNDARY_FILES or normalized in AUTH_SHELL_FILES:
        return True
    return any(normalized.startswith(prefix) for prefix in AUTH_BOUNDARY_PREFIXES)


def _extract_files(payload: dict[str, Any]) -> list[str]:
    candidates: list[Any] = []
    for key in ("files", "file_plan", "changes", "write_batch", "proposed_changes", "affected_files"):
        value = payload.get(key)
        if value:
            candidates.append(value)
    package = payload.get("package") if isinstance(payload.get("package"), dict) else {}
    if package.get("proposed_changes"):
        candidates.append(package["proposed_changes"])
    extracted: list[str] = []
    for candidate in candidates:
        if isinstance(candidate, str):
            extracted.append(candidate)
        elif isinstance(candidate, list):
            for item in candidate:
                if isinstance(item, str):
                    extracted.append(item)
                elif isinstance(item, dict):
                    path = item.get("path") or item.get("file") or item.get("filename")
                    if path:
                        extracted.append(str(path))
    return sorted({_normalize_path(path) for path in extracted if path})


def _normalize_path(path: str) -> str:
    clean = str(path).strip().replace("\\", "/").lstrip("/")
    return str(PurePosixPath(clean))
