from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Comment:
    comment_id: str
    tenant_id: str
    author_id: str
    target_type: str
    target_id: str
    body: str
    status: str


@dataclass(frozen=True)
class Mention:
    mention_id: str
    tenant_id: str
    comment_id: str
    mentioned_user_id: str
    status: str


@dataclass(frozen=True)
class Presence:
    presence_id: str
    tenant_id: str
    user_id: str
    location: str
    status: str
    seen_at: str


@dataclass(frozen=True)
class TimelineEntry:
    entry_id: str
    tenant_id: str
    source: str
    title: str
    created_at: str


@dataclass(frozen=True)
class AuditRecord:
    record_id: str
    tenant_id: str
    actor_id: str
    action: str
    target: str
    severity: str


@dataclass(frozen=True)
class CollabSummary:
    comment_count: int
    mention_count: int
    online_count: int
    timeline_count: int
    audit_count: int
    high_audit_count: int


@dataclass(frozen=True)
class CollabContext:
    comments: List[Comment]
    mentions: List[Mention]
    presences: List[Presence]
    timeline: List[TimelineEntry]
    audit_records: List[AuditRecord]
    metadata: Dict[str, object]
