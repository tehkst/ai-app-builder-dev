from __future__ import annotations

from typing import List

from app.platform.saas_portal.portal_models import CustomerProject, PortalCard, PortalView


def project_view(projects: List[CustomerProject]) -> PortalView:
    active = len([project for project in projects if project.status == "active"])
    cards = [
        PortalCard("project_count", "Projects", str(len(projects)), "active", {}),
        PortalCard("active_projects", "Active Projects", str(active), "healthy", {}),
    ]
    return PortalView("project_view", "Projects", cards)


def projects_for_tenant(projects: List[CustomerProject], tenant_id: str) -> List[CustomerProject]:
    return [project for project in projects if project.tenant_id == tenant_id]
