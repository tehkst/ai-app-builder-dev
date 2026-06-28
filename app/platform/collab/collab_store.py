from __future__ import annotations

from typing import Iterable, List

from app.platform.collab.collab_models import AuditRecord, CollabSummary, Comment, Mention, Presence, TimelineEntry


def comments_for_target(comments: Iterable[Comment], tenant_id: str, target_type: str, target_id: str) -> List[Comment]:
    return [
        comment
        for comment in comments
        if comment.tenant_id == tenant_id and comment.target_type == target_type and comment.target_id == target_id
    ]


def mentions_for_user(mentions: Iterable[Mention], tenant_id: str, user_id: str) -> List[Mention]:
    return [
        mention
        for mention in mentions
        if mention.tenant_id == tenant_id and mention.mentioned_user_id == user_id
    ]


def online_presence(presences: Iterable[Presence], tenant_id: str) -> List[Presence]:
    return [presence for presence in presences if presence.tenant_id == tenant_id and presence.status == "online"]


def timeline_for_tenant(entries: Iterable[TimelineEntry], tenant_id: str, limit: int = 10) -> List[TimelineEntry]:
    scoped = [entry for entry in entries if entry.tenant_id == tenant_id]
    return sorted(scoped, key=lambda entry: entry.created_at, reverse=True)[:limit]


def audit_for_tenant(records: Iterable[AuditRecord], tenant_id: str) -> List[AuditRecord]:
    return [record for record in records if record.tenant_id == tenant_id]


def summarize_collab(
    comments: Iterable[Comment],
    mentions: Iterable[Mention],
    presences: Iterable[Presence],
    timeline: Iterable[TimelineEntry],
    audit_records: Iterable[AuditRecord],
    tenant_id: str,
) -> CollabSummary:
    tenant_comments = [comment for comment in comments if comment.tenant_id == tenant_id]
    tenant_mentions = [mention for mention in mentions if mention.tenant_id == tenant_id]
    tenant_timeline = [entry for entry in timeline if entry.tenant_id == tenant_id]
    tenant_audit = audit_for_tenant(audit_records, tenant_id)
    return CollabSummary(
        comment_count=len(tenant_comments),
        mention_count=len(tenant_mentions),
        online_count=len(online_presence(presences, tenant_id)),
        timeline_count=len(tenant_timeline),
        audit_count=len(tenant_audit),
        high_audit_count=len([record for record in tenant_audit if record.severity == "high"]),
    )
