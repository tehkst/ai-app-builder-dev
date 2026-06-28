from __future__ import annotations

from app.platform.notify.notify_flow import run_demo_notices
from app.platform.notify.notify_store import enabled_channels, mark_read, notices_for_tenant, notices_for_user, summarize_notices, unread_notices


def main() -> None:
    data = run_demo_notices()
    assert len(data.notices) == 4, data
    assert len(data.preferences) == 3, data

    tenant_notices = notices_for_tenant(data.notices, "tenant_platform")
    assert len(tenant_notices) == 3, tenant_notices
    assert len(notices_for_tenant(data.notices, "missing")) == 0

    user_notices = notices_for_user(data.notices, "user_platform_owner")
    assert len(user_notices) == 3, user_notices
    assert len(unread_notices(user_notices)) == 2

    channels = enabled_channels(data.preferences, "user_platform_owner")
    assert channels == ["in_app", "email"], channels

    read_notice = mark_read(user_notices[0])
    assert read_notice.status == "read", read_notice

    summary = summarize_notices(user_notices, data.preferences)
    assert summary.notice_count == 3, summary
    assert summary.unread_count == 2, summary
    assert summary.sent_count == 1, summary
    assert summary.high_count == 1, summary
    assert summary.channel_count == 2, summary

    print("NOTICE CHECK PASSED")


if __name__ == "__main__":
    main()
