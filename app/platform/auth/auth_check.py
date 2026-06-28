from __future__ import annotations

from app.platform.auth.api_key_provider import api_key_is_active, issue_api_key
from app.platform.auth.audit_logger import AuditEvent, audit_events_for_tenant, record_audit_event
from app.platform.auth.authentication import authenticate_identity
from app.platform.auth.authorization import is_authorized, require_permission
from app.platform.auth.identity_provider import find_identity, identity_registry
from app.platform.auth.jwt_provider import issue_jwt_claims, validate_jwt_claims
from app.platform.auth.organization_service import find_organization, organization_registry
from app.platform.auth.permission_registry import permissions_for_role, role_has_permission
from app.platform.auth.role_registry import PLATFORM_OWNER, available_roles, role_registry
from app.platform.auth.session_manager import create_session, session_is_active
from app.platform.auth.tenant_service import tenant_registry, workspace_registry


def main() -> None:
    roles = role_registry()
    assert PLATFORM_OWNER in roles, roles
    assert PLATFORM_OWNER in available_roles()
    assert role_has_permission(PLATFORM_OWNER, "platform:admin") is True
    assert "platform:admin" in permissions_for_role(PLATFORM_OWNER)

    organizations = organization_registry()
    assert "org_platform" in organizations, organizations
    organization = find_organization("org_platform")
    assert organization.active is True

    tenants = tenant_registry()
    workspaces = workspace_registry()
    assert tenants["tenant_platform"].organization_id == "org_platform"
    assert workspaces["workspace_platform"].tenant_id == "tenant_platform"

    identities = identity_registry()
    assert "user_platform_owner" in identities, identities
    identity = find_identity("user_platform_owner")

    result = authenticate_identity(identity, "org_platform", "tenant_platform")
    assert result.success is True, result
    assert is_authorized(result.principal, "platform:admin") is True
    require_permission(result.principal, "platform:admin")

    claims = issue_jwt_claims(identity.user_id, "org_platform", "tenant_platform")
    assert validate_jwt_claims(claims) is True

    api_key = issue_api_key("key1", identity.user_id, "org_platform", "tenant_platform")
    assert api_key_is_active(api_key) is True

    session = create_session("session1", identity.user_id, "tenant_platform")
    assert session_is_active(session) is True

    event = AuditEvent(
        event_id="audit1",
        actor_user_id=identity.user_id,
        action="login",
        resource="session",
        tenant_id="tenant_platform",
        metadata={},
    )
    events = record_audit_event([], event)
    assert audit_events_for_tenant(events, "tenant_platform") == [event]

    print("AUTH CHECK PASSED")


if __name__ == "__main__":
    main()
