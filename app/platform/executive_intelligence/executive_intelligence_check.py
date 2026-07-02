from __future__ import annotations

from app.platform.executive_intelligence.service import (
    PRIMARY_REPOSITORY,
    build_executive_intelligence_briefing,
    build_executive_intelligence_summary,
)


def main() -> None:
    summary = build_executive_intelligence_summary()
    assert summary["milestone"] == "AEL-01"
    assert summary["status"] == "executive-intelligence-ready"
    assert summary["primary_repository"] == PRIMARY_REPOSITORY
    assert summary["readiness"]["repository_intelligence_ready"] is True
    assert "board_room_context_policy" in summary

    briefing = build_executive_intelligence_briefing()
    assert briefing["product"] == "Executive Intelligence Layer"
    assert briefing["live_sources"]["github_executor"]["payload"]["github_token_visible"] is False
    assert briefing["governance"]["main_branch_write_allowed"] is False
    assert briefing["governance"]["founder_approval_required"] is True
    assert briefing["governance"]["merge_allowed_by_executor"] is False
    assert briefing["architecture_signals"]["indexed_area_count"] >= 1
    assert "legacy_company_intelligence" in briefing["live_sources"]

    print("EXECUTIVE INTELLIGENCE CHECK PASSED")


if __name__ == "__main__":
    main()
