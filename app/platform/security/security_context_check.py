from __future__ import annotations

from app.platform.security.security_context import (
    ServicePrincipal,
    UserPrincipal,
    context_from_service_principal,
    context_from_user_principal,
)


def main() -> None:
    user = UserPrincipal(
        user_id="user1",
        email="owner@example.com",
        display_name="Owner",
        tenant_id="tenant1",
        organization_id="org1",
        roles=["platform_owner"],
    )
    user_context = context_from_user_principal(user, request_id="request1", trace_id="trace1")
    assert user_context.valid() is True
    assert user_context.actor_type == "user"
    assert user_context.has_role("platform_owner") is True
    assert user_context.belongs_to_tenant("tenant1") is True
    assert user_context.belongs_to_tenant("tenant2") is False

    service = ServicePrincipal(
        service_id="svc1",
        tenant_id="tenant1",
        organization_id="org1",
        scopes=["runtime:read"],
    )
    service_context = context_from_service_principal(service)
    assert service_context.valid() is True
    assert service_context.actor_type == "service"
    assert service_context.has_scope("runtime:read") is True
    assert service_context.has_role("platform_owner") is False

    print("D5.1 SECURITY CONTEXT CHECK PASSED")


if __name__ == "__main__":
    main()
