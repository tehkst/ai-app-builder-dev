from __future__ import annotations

from app.platform.saas_portal.portal_models import PortalCard, PortalView
from app.platform.workspace.workspace_models import WorkspaceContext
from app.platform.workspace.workspace_store import build_dashboard


def portal_workspace_view(context: WorkspaceContext, tenant_id: str, user_id: str) -> PortalView:
    dashboard = build_dashboard(
        tenant_id,
        user_id,
        context.tasks,
        context.favorites,
        context.search_documents,
        context.recent_items,
    )
    return PortalView(
        view_id="portal_workspace",
        title="Workspace",
        cards=[
            PortalCard("open", "Open Tasks", str(dashboard.open_tasks), "healthy", {}),
            PortalCard("favorites", "Favorites", str(dashboard.favorite_count), "healthy", {}),
            PortalCard("recent", "Recent", str(dashboard.recent_count), "healthy", {}),
            PortalCard("search", "Search Docs", str(dashboard.searchable_count), "healthy", {}),
        ],
    )
