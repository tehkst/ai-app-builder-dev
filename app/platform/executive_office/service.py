from __future__ import annotations

import os
from typing import Any, Dict


def build_executive_briefing() -> Dict[str, Any]:
    from app.platform.executive_intelligence.service import build_executive_intelligence_briefing

    state = build_executive_intelligence_briefing()
    return {
        "founder": os.getenv("FOUNDER_NAME", "Toni"),
        "company": state["company"],
        "status": "executive-office-live",
        "generated_at": state["generated_at"],
        "headline": _headline(state),
        "platform_health": state["platform_health"],
        "active_mission": state["active_mission"],
        "mission_stage": state["mission_stage"],
        "repository": {
            "identity": state["repository_identity"],
            "branch": state["branch"],
            "head_sha": state["head_sha"],
            "working_tree_status": state["working_tree_status"],
        },
        "blockers": state["blockers"],
        "risks": state["risks"],
        "next_focus": state["next_recommended_action"],
        "source": "executive_intelligence",
    }


def _headline(state: Dict[str, Any]) -> str:
    mission = state["active_mission"].get("value")
    if isinstance(mission, dict):
        return "Mission Control is tracking %s from current durable evidence." % (mission.get("title") or mission.get("mission_id") or "an active mission")
    return "Mission Control has no verified active mission in the current executive snapshot."
