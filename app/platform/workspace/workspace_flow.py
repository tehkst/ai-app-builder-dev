from __future__ import annotations

from app.platform.workspace.workspace_models import FavoriteItem, PersonalTask, RecentItem, SearchDocument, WorkspaceContext
from app.platform.workspace.workspace_store import build_dashboard


def run_demo_workspace() -> WorkspaceContext:
    tasks = [
        PersonalTask("task_workspace_1", "tenant_platform", "user_platform_owner", "Review generated app", "open", "high"),
        PersonalTask("task_workspace_2", "tenant_platform", "user_platform_owner", "Confirm deployment", "done", "medium"),
        PersonalTask("task_other", "other_tenant", "other_user", "Other task", "open", "low"),
    ]
    favorites = [
        FavoriteItem("fav1", "tenant_platform", "user_platform_owner", "application", "app_crm", "AI CRM App"),
        FavoriteItem("fav2", "tenant_platform", "user_platform_owner", "catalog", "template_crm", "AI CRM Starter"),
    ]
    documents = [
        SearchDocument("doc1", "tenant_platform", "AI CRM App", "Customer relationship workflow app.", "application"),
        SearchDocument("doc2", "tenant_platform", "Deployment Guide", "How to deploy generated applications.", "guide"),
        SearchDocument("doc3", "other_tenant", "Other Doc", "Other tenant content.", "guide"),
    ]
    recent_items = [
        RecentItem("recent1", "tenant_platform", "user_platform_owner", "application", "app_crm", "AI CRM App", "2026-06-28T10:00:00Z"),
        RecentItem("recent2", "tenant_platform", "user_platform_owner", "task", "task_workspace_1", "Review generated app", "2026-06-28T10:10:00Z"),
    ]
    dashboards = [
        build_dashboard("tenant_platform", "user_platform_owner", tasks, favorites, documents, recent_items)
    ]
    return WorkspaceContext(
        dashboards=dashboards,
        tasks=tasks,
        favorites=favorites,
        search_documents=documents,
        recent_items=recent_items,
        metadata={"flow": "workspace_pack"},
    )
