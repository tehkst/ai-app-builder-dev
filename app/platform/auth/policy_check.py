from __future__ import annotations

from app.platform.auth.policy_engine import ResourceRef, default_policy_engine
from app.platform.security.security_context import SecurityContext


def main() -> None:
    engine = default_policy_engine()
    resource = ResourceRef(
        resource_type="runtime",
        resource_id="runtime1",
        tenant_id="tenant1",
        metadata={},
    )

    owner = SecurityContext(
        tenant_id="tenant1",
        organization_id="org1",
        actor_id="user1",
        actor_type="user",
        roles=["platform_owner"],
    )
    assert engine.decide(owner, "platform:admin", resource).allowed is True
    assert engine.decide(owner, "runtime:read", resource).allowed is True

    service = SecurityContext(
        tenant_id="tenant1",
        organization_id="org1",
        actor_id="svc1",
        actor_type="service",
        scopes=["runtime:read"],
    )
    assert engine.decide(service, "runtime:read", resource).allowed is True
    assert engine.decide(service, "tenant:manage", resource).allowed is False

    other_tenant = SecurityContext(
        tenant_id="tenant2",
        organization_id="org1",
        actor_id="user2",
        actor_type="user",
        roles=["platform_owner"],
    )
    denied = engine.decide(other_tenant, "platform:admin", resource)
    assert denied.allowed is False
    assert denied.reason == "tenant mismatch"

    print("D5.3 POLICY CHECK PASSED")


if __name__ == "__main__":
    main()
