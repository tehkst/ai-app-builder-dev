from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_candidate(goal: str, outputs: Dict[str, Any]) -> Dict[str, Any]:
    sprint = outputs.get("sprint", {})
    committed = sprint.get("committed_stories", []) or []
    if committed:
        story = committed[0]
        return {
            "source": "sprint_engine",
            "title": story.get("title") or story.get("name") or goal,
            "reason": "First committed sprint story is available for the next governed mission.",
        }
    return {
        "source": "current_goal",
        "title": goal,
        "reason": "No committed sprint story was available, so Mission Runtime keeps the current goal as the next review candidate.",
    }


def build_runtime_mission_loop_plugin(goal: str, outputs: Dict[str, Any], requested_by: str = "founder") -> Dict[str, Any]:
    release_package = outputs.get("release_package", {})
    ready = bool(release_package)
    next_candidate = _next_candidate(goal, outputs)
    return {
        "roadmap_item": "BR-EXEC-05",
        "name": "Continuous Mission Loop",
        "status": "loop_package_ready" if ready else "blocked_pending_release_package",
        "goal": goal,
        "requested_by": requested_by,
        "created_at": _now(),
        "loop_flow": [
            {"stage": "release_result_review", "status": "waiting_for_release_report"},
            {"stage": "memory_update", "status": "blocked_until_release_result_reviewed"},
            {"stage": "sprint_closure", "status": "blocked_until_memory_update_ready"},
            {"stage": "next_mission_selection", "status": "blocked_until_sprint_closure"},
            {"stage": "founder_continue_gate", "status": "waiting_for_founder_approval"},
        ],
        "memory_update_package": {
            "ready": ready,
            "summary": "Record mission result, release status, lessons learned, and follow-up risks into Executive Memory.",
            "requires_release_report": True,
            "requires_founder_review": True,
        },
        "sprint_closure_package": {
            "ready": ready,
            "close_current_sprint_after_successful_release": True,
            "carry_forward_blocked_items": True,
            "requires_founder_review": True,
        },
        "next_mission_candidate": next_candidate,
        "governance": {
            "auto_start_next_mission": False,
            "requires_founder_continue_approval": True,
            "auto_merge": False,
            "auto_deploy": False,
            "external_review_required": True,
        },
        "next_action": {
            "owner": "founder" if ready else "mission_control",
            "action": "Review release result, approve memory update, then approve next mission start." if ready else "Complete BR-EXEC-04 release package first.",
        },
        "audit_trail": [
            {"event": "mission_loop_package_created", "timestamp": _now(), "actor": "mission_loop_plugin"},
            {"event": "founder_continue_gate_enforced", "timestamp": _now(), "actor": "governance"},
            {"event": "memory_update_gate_required", "timestamp": _now(), "actor": "governance"},
        ],
    }
