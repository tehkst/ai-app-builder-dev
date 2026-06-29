from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class UserPrincipal:
    user_id: str
    email: str
    display_name: str
    tenant_id: str
    organization_id: str
    roles: List[str] = field(default_factory=list)

    def has_role(self, role: str) -> bool:
        return role in self.roles


@dataclass(frozen=True)
class ServicePrincipal:
    service_id: str
    tenant_id: str
    organization_id: str
    scopes: List[str] = field(default_factory=list)

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


@dataclass(frozen=True)
class SecurityContext:
    tenant_id: str
    organization_id: str
    actor_id: str
    actor_type: str
    roles: List[str] = field(default_factory=list)
    scopes: List[str] = field(default_factory=list)
    request_id: str = ""
    trace_id: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)

    def valid(self) -> bool:
        return all([self.tenant_id, self.organization_id, self.actor_id, self.actor_type])

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def belongs_to_tenant(self, tenant_id: str) -> bool:
        return self.tenant_id == tenant_id


def context_from_user_principal(
    principal: UserPrincipal,
    request_id: str = "",
    trace_id: str = "",
    metadata: Optional[Dict[str, str]] = None,
) -> SecurityContext:
    return SecurityContext(
        tenant_id=principal.tenant_id,
        organization_id=principal.organization_id,
        actor_id=principal.user_id,
        actor_type="user",
        roles=list(principal.roles),
        request_id=request_id,
        trace_id=trace_id,
        metadata=metadata or {},
    )


def context_from_service_principal(
    principal: ServicePrincipal,
    request_id: str = "",
    trace_id: str = "",
    metadata: Optional[Dict[str, str]] = None,
) -> SecurityContext:
    return SecurityContext(
        tenant_id=principal.tenant_id,
        organization_id=principal.organization_id,
        actor_id=principal.service_id,
        actor_type="service",
        scopes=list(principal.scopes),
        request_id=request_id,
        trace_id=trace_id,
        metadata=metadata or {},
    )
