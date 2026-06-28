from __future__ import annotations

from typing import Iterable, List

from app.platform.workspace.workspace_models import (
    FavoriteItem,
    PersonalTask,
    RecentItem,
    SearchDocument,
    WorkspaceDashboard,
    WorkspaceSummary,
)


def tasks_for_user(tasks: Iterable[PersonalTask], tenant_id: str, user_id: str) -> List[PersonalTask]:
    return [task for task in tasks if task.tenant_id == tenant_id and task.user_id == user_id]


def open_tasks(tasks: Iterable[PersonalTask]) -> List[PersonalTask]:
    return [task for task in tasks if task.status != "done"]


def favorites_for_user(favorites: Iterable[FavoriteItem], tenant_id: str, user_id: str) -> List[FavoriteItem]:
    return [item for item in favorites if item.tenant_id == tenant_id and item.user_id == user_id]


def recent_for_user(recent_items: Iterable[RecentItem], tenant_id: str, user_id: str, limit: int = 5) -> List[RecentItem]:
    scoped = [item for item in recent_items if item.tenant_id == tenant_id and item.user_id == user_id]
    return sorted(scoped, key=lambda item: item.opened_at, reverse=True)[:limit]


def search_documents(documents: Iterable[SearchDocument], tenant_id: str, query: str) -> List[SearchDocument]:
    text = query.lower()
    return [
        document
        for document in documents
        if document.tenant_id == tenant_id and (text in document.title.lower() or text in document.body.lower())
    ]


def build_dashboard(
    tenant_id: str,
    user_id: str,
    tasks: Iterable[PersonalTask],
    favorites: Iterable[FavoriteItem],
    documents: Iterable[SearchDocument],
    recent_items: Iterable[RecentItem],
) -> WorkspaceDashboard:
    user_tasks = tasks_for_user(tasks, tenant_id, user_id)
    user_favorites = favorites_for_user(favorites, tenant_id, user_id)
    tenant_documents = [document for document in documents if document.tenant_id == tenant_id]
    user_recent = recent_for_user(recent_items, tenant_id, user_id)
    return WorkspaceDashboard(
        tenant_id=tenant_id,
        user_id=user_id,
        open_tasks=len(open_tasks(user_tasks)),
        favorite_count=len(user_favorites),
        recent_count=len(user_recent),
        searchable_count=len(tenant_documents),
    )


def summarize_workspace(
    dashboards: Iterable[WorkspaceDashboard],
    tasks: Iterable[PersonalTask],
    favorites: Iterable[FavoriteItem],
    documents: Iterable[SearchDocument],
    recent_items: Iterable[RecentItem],
) -> WorkspaceSummary:
    task_list = list(tasks)
    return WorkspaceSummary(
        dashboard_count=len(list(dashboards)),
        task_count=len(task_list),
        open_task_count=len(open_tasks(task_list)),
        favorite_count=len(list(favorites)),
        search_document_count=len(list(documents)),
        recent_count=len(list(recent_items)),
    )
