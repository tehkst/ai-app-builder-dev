from __future__ import annotations

from typing import Dict

from app.platform.auth.tenant_models import Tenant, Workspace


def create_tenant(tenant_id: str, organization_id: str, name: str) -> Tenant:
    return Tenant(tenant_id=tenant_id, organization_id=organization_id, name=name)


def create_workspace(workspace_id: str, tenant_id: str, name: str) -> Workspace:
    return Workspace(workspace_id=workspace_id, tenant_id=tenant_id, name=name)


def tenant_registry() -> Dict[str, Tenant]:
    tenant = create_tenant("tenant_platform", "org_platform", "Platform Tenant")
    return {tenant.tenant_id: tenant}


def workspace_registry() -> Dict[str, Workspace]:
    workspace = create_workspace("workspace_platform", "tenant_platform", "Platform Workspace")
    return {workspace.workspace_id: workspace}
