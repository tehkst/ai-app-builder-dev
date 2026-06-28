from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Identity:
    user_id: str
    email: str
    display_name: str
    active: bool = True


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    identity: Identity
    organization_id: str
    tenant_id: str
    roles: List[str]


@dataclass(frozen=True)
class AuthResult:
    success: bool
    principal: AuthenticatedPrincipal
    reason: str = ""
