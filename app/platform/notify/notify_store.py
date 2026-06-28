from __future__ import annotations

from typing import Iterable, List

from app.platform.notify.notify_models import Notice, NoticePreference, NoticeSummary


def make_notice(
    notice_id: str,
    tenant_id: str,
    user_id: str,
    channel: str,
    title: str,
    body: str,
    severity: str,
    status: str = "unread",
) -> Notice:
    return Notice(notice_id, tenant_id, user_id, channel, title, body, severity, status)


def make_preference(user_id: str, channel: str, enabled: bool) -> NoticePreference:
    return NoticePreference(user_id, channel, enabled)


def notices_for_tenant(notices: Iterable[Notice], tenant_id: str) -> List[Notice]:
    return [notice for notice in notices if notice.tenant_id == tenant_id]


def notices_for_user(notices: Iterable[Notice], user_id: str) -> List[Notice]:
    return [notice for notice in notices if notice.user_id == user_id]


def unread_notices(notices: Iterable[Notice]) -> List[Notice]:
    return [notice for notice in notices if notice.status == "unread"]


def enabled_channels(preferences: Iterable[NoticePreference], user_id: str) -> List[str]:
    return [preference.channel for preference in preferences if preference.user_id == user_id and preference.enabled]


def summarize_notices(notices: Iterable[Notice], preferences: Iterable[NoticePreference]) -> NoticeSummary:
    notice_list = list(notices)
    preference_list = list(preferences)
    channels = {preference.channel for preference in preference_list if preference.enabled}
    return NoticeSummary(
        notice_count=len(notice_list),
        unread_count=len([notice for notice in notice_list if notice.status == "unread"]),
        sent_count=len([notice for notice in notice_list if notice.status == "sent"]),
        high_count=len([notice for notice in notice_list if notice.severity == "high"]),
        channel_count=len(channels),
    )


def mark_read(notice: Notice) -> Notice:
    return Notice(
        notice.notice_id,
        notice.tenant_id,
        notice.user_id,
        notice.channel,
        notice.title,
        notice.body,
        notice.severity,
        "read",
    )
