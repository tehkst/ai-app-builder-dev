from __future__ import annotations

from app.platform.launch.launch_models import LaunchContext
from app.platform.launch.launch_store import launch_is_ready, summarize_launch
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def portal_launch_view(context: LaunchContext) -> PortalView:
    summary = summarize_launch(context.documentation, context.packages, context.signals)
    ready = "ready" if launch_is_ready(context.signals) else "blocked"
    return PortalView(
        view_id="portal_launch",
        title="Version 1.0",
        cards=[
            PortalCard("docs", "Documentation", str(summary.ready_documentation_count), "healthy", {}),
            PortalCard("packages", "Packages", str(summary.published_package_count), "healthy", {}),
            PortalCard("launch", "Launch", ready, "healthy", {}),
        ],
    )
