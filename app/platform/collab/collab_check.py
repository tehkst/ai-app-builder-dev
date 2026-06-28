from __future__ import annotations

from app.platform.collab.collab_flow import run_demo_collab
from app.platform.collab.collab_store import (
    audit_for_tenant,
    comments_for_target,
    mentions_for_user,
    online_presence,
    summarize_collab,
    timeline_for_tenant,
)


def main() -> None:
    data = run_demo_collab()
    assert len(data.comments) == 3, data
    assert len(data.mentions) == 2, data
    assert len(data.presences) == 3, data
    assert len(data.timeline) == 3, data
    assert len(data.audit_records) == 3, data

    comments = comments_for_target(data.comments, "tenant_platform", "application", "app_crm")
    assert len(comments) == 1, comments

    mentions = mentions_for_user(data.mentions, "tenant_platform", "user_platform_owner")
    assert len(mentions) == 2, mentions

    online = online_presence(data.presences, "tenant_platform")
    assert len(online) == 1, online

    timeline = timeline_for_tenant(data.timeline, "tenant_platform")
    assert timeline[0].entry_id == "timeline3", timeline

    audit = audit_for_tenant(data.audit_records, "tenant_platform")
    assert len(audit) == 2, audit

    summary = summarize_collab(data.comments, data.mentions, data.presences, data.timeline, data.audit_records, "tenant_platform")
    assert summary.comment_count == 2, summary
    assert summary.mention_count == 2, summary
    assert summary.online_count == 1, summary
    assert summary.timeline_count == 3, summary
    assert summary.audit_count == 2, summary
    assert summary.high_audit_count == 1, summary

    print("COLLAB PACK CHECK PASSED")


if __name__ == "__main__":
    main()
