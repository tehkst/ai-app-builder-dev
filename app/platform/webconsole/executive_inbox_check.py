from __future__ import annotations

from datetime import datetime, timezone

from app.platform.webconsole.executive_inbox_view import executive_inbox_view
from app.platform.webconsole.navigation import admin_navigation, navigation_routes


def main() -> None:
    assert "/admin/inbox" in navigation_routes()
    assert next(page for page in admin_navigation() if page.page_id == "inbox").title == "Executive Inbox"

    now = datetime(2026, 7, 22, 6, 30, tzinfo=timezone.utc)
    view = executive_inbox_view(
        sources={
            "approval": [
                {
                    "approval_id": "APP-1",
                    "title": "Approve AFOS-004 scope",
                    "action_required": "Approve mission",
                    "status": "pending",
                    "created_at": "2026-07-22T05:30:00Z",
                    "mission_id": "AFOS-004",
                    "owner": "Founder Approval",
                }
            ],
            "workflow": [
                {
                    "authority_reference": "approval:APP-1",
                    "workflow_id": "WF-1",
                    "title": "Duplicate approval projection",
                    "action_required": "Approve mission",
                    "status": "pending",
                    "created_at": "2026-07-22T05:40:00Z",
                    "priority": "medium",
                }
            ],
            "incident": [
                {
                    "incident_id": "INC-9",
                    "title": "Production verification blocked",
                    "next_action": "Review incident",
                    "status": "blocked",
                    "created_at": "2026-07-22T04:30:00Z",
                }
            ],
            "agent_task": [
                {
                    "agent_task_id": "TASK-3",
                    "title": "Architecture review",
                    "next_action": "Review agent output",
                    "status": "ready",
                    "created_at": "2026-07-22T06:00:00Z",
                    "agent": "AI CTO",
                    "mission_id": "AFOS-004",
                }
            ],
        },
        now=now,
    )

    assert view.view_id == "executive_inbox"
    assert view.title == "Executive Inbox"
    assert len(view.cards) == 3, view
    assert view.cards[0].metadata["source"] == "incident", view.cards[0]
    assert view.cards[0].metadata["priority"] == "critical", view.cards[0]
    approval = next(card for card in view.cards if card.metadata["authority_reference"] == "approval:APP-1")
    assert approval.metadata["owns_state"] is False
    assert approval.metadata["stores_items"] is False
    assert approval.metadata["mission_id"] == "AFOS-004"
    assert approval.metadata["route"] == "/admin/approvals"
    assert approval.metadata["age_minutes"] == 60

    empty = executive_inbox_view(sources={}, now=now)
    assert len(empty.cards) == 1
    assert empty.cards[0].value == "No founder action required"
    assert empty.cards[0].metadata["refresh_behavior"] == "rebuild-from-existing-sources"

    print("EXECUTIVE INBOX CHECK PASSED")


if __name__ == "__main__":
    main()
