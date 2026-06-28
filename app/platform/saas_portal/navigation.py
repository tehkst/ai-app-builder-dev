from __future__ import annotations

from typing import List

from app.platform.saas_portal.portal_models import PortalPage


def portal_navigation() -> List[PortalPage]:
    return [
        PortalPage("dashboard", "Dashboard", "/portal", "overview"),
        PortalPage("projects", "Projects", "/portal/projects", "workspace"),
        PortalPage("applications", "AI Applications", "/portal/apps", "workspace"),
        PortalPage("lifecycle", "Lifecycle", "/portal/lifecycle", "workspace"),
        PortalPage("account_plan", "Account Plan", "/portal/account-plan", "account"),
        PortalPage("deployments", "Deployments", "/portal/deployments", "operations"),
        PortalPage("runtime", "Runtime", "/portal/runtime", "operations"),
        PortalPage("api_keys", "Keys", "/portal/api-keys", "security"),
        PortalPage("settings", "Settings", "/portal/settings", "account"),
    ]


def portal_routes() -> List[str]:
    return [page.route for page in portal_navigation()]
