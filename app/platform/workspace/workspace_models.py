from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class WorkspaceDashboard:
    tenant_id: str
    user_id: str
    open_tasks: int
    favorite_count: int
    recent_count: int
    searchable_count: int


@dataclass(frozen=True)
class PersonalTask:
    task_id: str
    tenant_id: str
    user_id: str
    title: str
    status: str
    priority: str


@dataclass(frozen=True)
class FavoriteItem:
    favorite_id: str
    tenant_id: str
    user_id: str
    target_type: str
    target_id: str
    title: str


@dataclass(frozen=True)
class SearchDocument:
    document_id: str
    tenant_id: str
    title: str
    body: str
    source: str


@dataclass(frozen=True)
class RecentItem:
    recent_id: str
    tenant_id: str
    user_id: str
    target_type: str
    target_id: str
    title: str
    opened_at: str


@dataclass(frozen=True)
class WorkspaceSummary:
    dashboard_count: int
    task_count: int
    open_task_count: int
    favorite_count: int
    search_document_count: int
    recent_count: int


@dataclass(frozen=True)
class WorkspaceContext:
    dashboards: List[WorkspaceDashboard]
    tasks: List[PersonalTask]
    favorites: List[FavoriteItem]
    search_documents: List[SearchDocument]
    recent_items: List[RecentItem]
    metadata: Dict[str, object]
