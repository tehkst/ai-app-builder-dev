from __future__ import annotations

from app.platform.collab.collab_models import AuditRecord, CollabContext, Comment, Mention, Presence, TimelineEntry


def run_demo_collab() -> CollabContext:
    comments = [
        Comment("comment1", "tenant_platform", "user_platform_owner", "application", "app_crm", "Looks ready for review.", "open"),
        Comment("comment2", "tenant_platform", "user_platform_owner", "task", "task_workspace_1", "Please confirm deployment.", "open"),
        Comment("comment3", "other_tenant", "other_user", "task", "other_task", "Other comment.", "open"),
    ]
    mentions = [
        Mention("mention1", "tenant_platform", "comment1", "user_platform_owner", "unread"),
        Mention("mention2", "tenant_platform", "comment2", "user_platform_owner", "read"),
    ]
    presences = [
        Presence("presence1", "tenant_platform", "user_platform_owner", "portal/workspace", "online", "2026-06-28T10:00:00Z"),
        Presence("presence2", "tenant_platform", "user_reviewer", "admin/tasks", "away", "2026-06-28T10:02:00Z"),
        Presence("presence3", "other_tenant", "other_user", "portal", "online", "2026-06-28T10:03:00Z"),
    ]
    timeline = [
        TimelineEntry("timeline1", "tenant_platform", "comment", "Comment added", "2026-06-28T10:10:00Z"),
        TimelineEntry("timeline2", "tenant_platform", "mention", "Mention created", "2026-06-28T10:11:00Z"),
        TimelineEntry("timeline3", "tenant_platform", "presence", "User came online", "2026-06-28T10:12:00Z"),
    ]
    audit_records = [
        AuditRecord("audit1", "tenant_platform", "user_platform_owner", "comment_created", "app_crm", "low"),
        AuditRecord("audit2", "tenant_platform", "user_platform_owner", "permission_checked", "app_crm", "high"),
        AuditRecord("audit3", "other_tenant", "other_user", "comment_created", "other_task", "low"),
    ]
    return CollabContext(
        comments=comments,
        mentions=mentions,
        presences=presences,
        timeline=timeline,
        audit_records=audit_records,
        metadata={"flow": "collab_pack"},
    )
