from __future__ import annotations

from app.platform.auth.auth_models import AuthenticatedPrincipal
from app.platform.auth.permission_registry import role_has_permission


def is_authorized(principal: AuthenticatedPrincipal, permission: str) -> bool:
    return any(role_has_permission(role, permission) for role in principal.roles)


def require_permission(principal: AuthenticatedPrincipal, permission: str) -> None:
    if not is_authorized(principal, permission):
        raise PermissionError(f"Permission denied: {permission}")
