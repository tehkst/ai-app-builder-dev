from __future__ import annotations

from typing import List

from app.platform.saas_portal.portal_models import CustomerApplication, PortalCard, PortalView


def application_view(applications: List[CustomerApplication]) -> PortalView:
    deployed = len([app for app in applications if app.status == "deployed"])
    cards = [
        PortalCard("application_count", "AI Applications", str(len(applications)), "active", {}),
        PortalCard("deployed_applications", "Deployed Applications", str(deployed), "healthy", {}),
    ]
    return PortalView("application_view", "AI Applications", cards)


def applications_for_tenant(applications: List[CustomerApplication], tenant_id: str) -> List[CustomerApplication]:
    return [app for app in applications if app.tenant_id == tenant_id]
