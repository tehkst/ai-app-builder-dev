from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Organization:
    organization_id: str
    name: str
    active: bool = True


@dataclass(frozen=True)
class Tenant:
    tenant_id: str
    organization_id: str
    name: str
    active: bool = True


@dataclass(frozen=True)
class Workspace:
    workspace_id: str
    tenant_id: str
    name: str
    active: bool = True
