from __future__ import annotations

from app.platform.webconsole.console_models import ConsoleCard, ConsoleView
from app.platform.workspace.workspace_models import WorkspaceContext
from app.platform.workspace.workspace_store import summarize_workspace


def admin_workspace_view(context: WorkspaceContext) -> ConsoleView:
    summary = summarize_workspace(
        context.dashboards,
        context.tasks,
        context.favorites,
        context.search_documents,
        context.recent_items,
    )
    return ConsoleView(
        view_id="admin_workspace",
        title="Workspace",
        cards=[
            ConsoleCard("dashboards", "Dashboards", str(summary.dashboard_count), "healthy", {}),
            ConsoleCard("tasks", "Tasks", str(summary.task_count), "healthy", {}),
            ConsoleCard("open", "Open Tasks", str(summary.open_task_count), "healthy", {}),
            ConsoleCard("favorites", "Favorites", str(summary.favorite_count), "healthy", {}),
            ConsoleCard("search", "Search Docs", str(summary.search_document_count), "healthy", {}),
            ConsoleCard("recent", "Recent", str(summary.recent_count), "healthy", {}),
        ],
    )
