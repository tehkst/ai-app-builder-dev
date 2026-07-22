from __future__ import annotations

from datetime import datetime, timezone

from app.platform.executive_intelligence.proactive_briefing import build_proactive_jarvis_briefing


def main() -> None:
    now = datetime(2026, 7, 22, 7, 0, tzinfo=timezone.utc)
    snapshot = {
        "generated_at": "2026-07-22T06:55:00+00:00",
        "blockers": [
            {
                "title": "Production verification missing",
                "status": "blocked",
                "value": "Verify the deployed revision before claiming completion.",
                "source": "production_verification",
                "checked_at": "2026-07-22T06:50:00+00:00",
            }
        ],
        "risks": [
            {
                "title": "Stale release signal",
                "status": "observed",
                "value": "Release evidence is old.",
                "source": "release_authority",
                "checked_at": "2026-07-22T02:00:00+00:00",
            }
        ],
        "active_mission": {
            "status": "observed",
            "value": {"mission_id": "AFOS-005", "status": "running"},
            "source": "mission_pipeline",
            "checked_at": "2026-07-22T06:58:00+00:00",
            "freshness": "checked-on-request",
        },
        "mission_stage": {
            "status": "observed",
            "value": "implementation",
            "source": "mission_pipeline",
            "checked_at": "2026-07-22T06:58:00+00:00",
            "freshness": "checked-on-request",
        },
        "production_verification": {
            "status": "unknown",
            "value": None,
            "source": "production_verification",
            "checked_at": "2026-07-22T06:50:00+00:00",
            "freshness": "checked-on-request",
            "unknown_reason": "No authoritative production verification exists.",
        },
        "next_recommended_action": {
            "status": "observed",
            "value": "Review the pending founder approval.",
            "source": "executive_intelligence",
            "checked_at": "2026-07-22T06:59:00+00:00",
            "freshness": "checked-on-request",
        },
    }
    inbox_sources = {
        "approval": [
            {
                "approval_id": "APP-5",
                "authority_reference": "approval:APP-5",
                "title": "Approve AFOS-005",
                "action_required": "Approve mission",
                "status": "pending",
                "priority": "high",
                "created_at": "2026-07-22T06:45:00Z",
                "route": "/admin/approvals",
                "owner": "Founder Approval",
                "mission_id": "AFOS-005",
            },
            {
                "approval_id": "APP-5",
                "authority_reference": "approval:APP-5",
                "title": "Duplicate approval projection",
                "action_required": "Approve mission",
                "status": "pending",
                "priority": "medium",
                "created_at": "2026-07-22T06:46:00Z",
            },
        ],
        "workflow": [
            {
                "workflow_id": "WF-9",
                "title": "CI repair blocked",
                "next_action": "Review validation errors",
                "status": "failed",
                "created_at": "2026-07-22T06:40:00Z",
                "priority": "critical",
                "route": "/admin/tasks",
            }
        ],
    }

    briefing = build_proactive_jarvis_briefing(snapshot, inbox_sources=inbox_sources, now=now)
    assert briefing["milestone"] == "AFOS-005"
    assert briefing["briefing_mode"] == "on-request-composition"
    assert briefing["summary"]["critical_items"] >= 2
    assert briefing["summary"]["pending_approvals"] >= 1
    assert briefing["summary"]["failed_or_blocked_workflows"] == 1
    assert briefing["summary"]["stale_signals"] >= 1
    assert len([item for item in briefing["priorities"] if item["authority_reference"] == "approval:APP-5"]) == 1
    approval = next(item for item in briefing["pending_approvals"] if item["authority_reference"] == "approval:APP-5")
    assert approval["route"] == "/admin/approvals"
    stale_risk = next(item for item in briefing["risks"] if item["title"] == "Stale release signal")
    assert stale_risk["stale"] is True
    assert briefing["governance"]["owns_state"] is False
    assert briefing["governance"]["stores_briefings"] is False
    assert briefing["governance"]["scheduler_created"] is False
    assert briefing["governance"]["source_systems_authoritative"] is True
    assert any(action["route"] == "/admin/approvals" for action in briefing["next_actions"])

    print("PROACTIVE JARVIS BRIEFING CHECK PASSED")


if __name__ == "__main__":
    main()
