from __future__ import annotations

from app.platform.workspace.workspace_flow import run_demo_workspace
from app.platform.workspace.workspace_store import (
    build_dashboard,
    favorites_for_user,
    recent_for_user,
    search_documents,
    summarize_workspace,
    tasks_for_user,
)


def main() -> None:
    data = run_demo_workspace()
    assert len(data.dashboards) == 1, data
    assert len(data.tasks) == 3, data
    assert len(data.favorites) == 2, data
    assert len(data.search_documents) == 3, data
    assert len(data.recent_items) == 2, data

    user_tasks = tasks_for_user(data.tasks, "tenant_platform", "user_platform_owner")
    assert len(user_tasks) == 2, user_tasks

    user_favorites = favorites_for_user(data.favorites, "tenant_platform", "user_platform_owner")
    assert len(user_favorites) == 2, user_favorites

    results = search_documents(data.search_documents, "tenant_platform", "deploy")
    assert len(results) == 1, results
    assert results[0].document_id == "doc2", results

    recent = recent_for_user(data.recent_items, "tenant_platform", "user_platform_owner")
    assert recent[0].recent_id == "recent2", recent

    dashboard = build_dashboard("tenant_platform", "user_platform_owner", data.tasks, data.favorites, data.search_documents, data.recent_items)
    assert dashboard.open_tasks == 1, dashboard
    assert dashboard.favorite_count == 2, dashboard
    assert dashboard.recent_count == 2, dashboard
    assert dashboard.searchable_count == 2, dashboard

    summary = summarize_workspace(data.dashboards, data.tasks, data.favorites, data.search_documents, data.recent_items)
    assert summary.dashboard_count == 1, summary
    assert summary.task_count == 3, summary
    assert summary.open_task_count == 2, summary
    assert summary.favorite_count == 2, summary
    assert summary.search_document_count == 3, summary
    assert summary.recent_count == 2, summary

    print("WORKSPACE PACK CHECK PASSED")


if __name__ == "__main__":
    main()
