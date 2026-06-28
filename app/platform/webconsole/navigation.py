from __future__ import annotations

from typing import List

from app.platform.webconsole.console_models import ConsolePage


def admin_navigation() -> List[ConsolePage]:
    return [
        ConsolePage("dashboard", "Executive Dashboard", "/admin", "overview"),
        ConsolePage("operations", "Operations", "/admin/operations", "operations"),
        ConsolePage("runtime", "Runtime", "/admin/runtime", "operations"),
        ConsolePage("deployment", "Deployments", "/admin/deployments", "operations"),
        ConsolePage("pmo", "PMO", "/admin/pmo", "planning"),
        ConsolePage("registry", "Registry", "/admin/registry", "platform"),
        ConsolePage("agents", "Agents", "/admin/agents", "platform"),
        ConsolePage("plugins", "Plugins", "/admin/plugins", "platform"),
    ]


def navigation_routes() -> List[str]:
    return [page.route for page in admin_navigation()]
