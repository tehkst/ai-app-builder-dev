from __future__ import annotations

from app.platform.auth.auth_models import AuthResult, AuthenticatedPrincipal, Identity
from app.platform.auth.role_registry import PLATFORM_OWNER


def authenticate_identity(identity: Identity, organization_id: str, tenant_id: str) -> AuthResult:
    principal = AuthenticatedPrincipal(
        identity=identity,
        organization_id=organization_id,
        tenant_id=tenant_id,
        roles=[PLATFORM_OWNER],
    )
    if not identity.active:
        return AuthResult(success=False, principal=principal, reason="identity inactive")
    return AuthResult(success=True, principal=principal)
