from __future__ import annotations

from typing import Dict, List

from app.platform.auth.role_registry import (
    AUDITOR,
    DEVELOPER,
    OPERATOR,
    ORGANIZATION_ADMIN,
    ORGANIZATION_OWNER,
    PLATFORM_ADMIN,
    PLATFORM_OWNER,
    PROJECT_MANAGER,
    VIEWER,
)

PERMISSIONS = [
    "platform:admin",
    "organization:admin",
    "tenant:manage",
    "project:manage",
    "runtime:execute",
    "deployment:manage",
    "registry:read",
    "registry:write",
    "plugin:manage",
    "audit:view",
]

ROLE_PERMISSIONS: Dict[str, List[str]] = {
    PLATFORM_OWNER: list(PERMISSIONS),
    PLATFORM_ADMIN: list(PERMISSIONS),
    ORGANIZATION_OWNER: ["organization:admin", "tenant:manage", "project:manage", "runtime:execute", "deployment:manage", "registry:read", "audit:view"],
    ORGANIZATION_ADMIN: ["tenant:manage", "project:manage", "runtime:execute", "deployment:manage", "registry:read"],
    PROJECT_MANAGER: ["project:manage", "registry:read"],
    DEVELOPER: ["runtime:execute", "deployment:manage", "registry:read"],
    OPERATOR: ["runtime:execute", "deployment:manage", "audit:view"],
    VIEWER: ["registry:read"],
    AUDITOR: ["audit:view", "registry:read"],
}


def permissions_for_role(role: str) -> List[str]:
    return list(ROLE_PERMISSIONS.get(role, []))


def role_has_permission(role: str, permission: str) -> bool:
    return permission in permissions_for_role(role)
