from __future__ import annotations

from typing import Any, Dict


def build_company_intelligence_snapshot() -> Dict[str, Any]:
    """Compatibility projection of the canonical Executive Intelligence snapshot."""
    from app.platform.executive_intelligence.service import build_executive_intelligence_briefing

    executive = build_executive_intelligence_briefing()
    return {
        "milestone": "INT-01-COMPATIBILITY",
        "status": "company-intelligence-derived",
        "generated_at": executive["generated_at"],
        "company": executive["company"],
        "primary_repository": executive["repository_identity"]["value"],
        "executive_summary": {
            "platform_stage": executive["mission_stage"],
            "project_progress": executive["project_progress"],
            "primary_blockers": executive["blockers"],
            "risks": executive["risks"],
            "next_recommended_action": executive["next_recommended_action"],
        },
        "capability_inventory": executive["source_evidence"]["capabilities"],
        "raw_status": executive,
        "source": "executive_intelligence",
        "authoritative": False,
        "compatibility_projection": True,
    }


def build_company_intelligence_summary() -> Dict[str, Any]:
    snapshot = build_company_intelligence_snapshot()
    return {
        "milestone": snapshot["milestone"],
        "status": snapshot["status"],
        "primary_repository": snapshot["primary_repository"],
        "project_progress": snapshot["executive_summary"]["project_progress"],
        "blockers": snapshot["executive_summary"]["primary_blockers"],
        "source": snapshot["source"],
        "authoritative": False,
    }
