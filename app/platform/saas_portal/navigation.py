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
        PortalPage("store", "Store", "/portal/store", "workspace"),
        PortalPage("tasks", "Tasks", "/portal/tasks", "workspace"),
        PortalPage("activity", "Activity", "/portal/activity", "workspace"),
        PortalPage("notices", "Notices", "/portal/notices", "workspace"),
        PortalPage("preferences", "Preferences", "/portal/preferences", "account"),
        PortalPage("onboarding", "Getting Started", "/portal/onboarding", "workspace"),
        PortalPage("workspace_home", "Workspace", "/portal/workspace", "workspace"),
        PortalPage("collab", "Collaboration", "/portal/collaboration", "workspace"),
        PortalPage("adminops", "Administration", "/portal/administration", "account"),
        PortalPage("opscenter", "Operations", "/portal/operations", "operations"),
        PortalPage("release", "Release Notes", "/portal/releases", "account"),
        PortalPage("deployments", "Deployments", "/portal/deployments", "operations"),
        PortalPage("runtime", "Runtime", "/portal/runtime", "operations"),
        PortalPage("settings", "Settings", "/portal/settings", "account"),
    ]


def portal_routes() -> List[str]:
    return [page.route for page in portal_navigation()]
