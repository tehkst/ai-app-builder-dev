from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from app.platform.auth.permission_registry import permissions_for_role
from app.platform.auth.role_registry import available_roles
from app.platform.security.security_context import SecurityContext


@dataclass(frozen=True)
class ResourceRef:
    resource_type: str
    resource_id: str
    tenant_id: str
    metadata: Dict[str, str]


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class PolicyRule:
    name: str
    permission: str
    roles: List[str]
    scopes: List[str]

    def allows(self, context: SecurityContext, permission: str) -> bool:
        if self.permission != permission:
            return False
        return any(context.has_role(role) for role in self.roles) or any(context.has_scope(scope) for scope in self.scopes)


class PolicyEngine:
    def __init__(self, rules: List[PolicyRule]) -> None:
        self._rules = list(rules)

    def decide(self, context: SecurityContext, permission: str, resource: ResourceRef) -> PolicyDecision:
        if not context.valid():
            return PolicyDecision(False, "invalid context")
        if not context.belongs_to_tenant(resource.tenant_id):
            return PolicyDecision(False, "tenant mismatch")
        for rule in self._rules:
            if rule.allows(context, permission):
                return PolicyDecision(True, rule.name)
        return PolicyDecision(False, "no matching policy")


def default_policy_engine() -> PolicyEngine:
    rules: List[PolicyRule] = []
    for role in available_roles():
        for permission in permissions_for_role(role):
            rules.append(PolicyRule(f"{role}:{permission}", permission, [role], []))
    rules.append(PolicyRule("runtime scope read", "runtime:read", [], ["runtime:read"]))
    return PolicyEngine(rules)
