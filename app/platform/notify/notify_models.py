from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Notice:
    notice_id: str
    tenant_id: str
    user_id: str
    channel: str
    title: str
    body: str
    severity: str
    status: str


@dataclass(frozen=True)
class NoticePreference:
    user_id: str
    channel: str
    enabled: bool


@dataclass(frozen=True)
class NoticeSummary:
    notice_count: int
    unread_count: int
    sent_count: int
    high_count: int
    channel_count: int


@dataclass(frozen=True)
class NoticeContext:
    notices: List[Notice]
    preferences: List[NoticePreference]
    metadata: Dict[str, object]
