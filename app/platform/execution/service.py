from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.platform.auth.service import require_founder


STAGES = [
    "intent_received",
    "requirements_clarified",
    "scope_of_work",
    "architecture_review",
    "implementation_plan",
    "validation_plan",
    "founder_approval_required",
    "ready_for_execution",
]

_ACTIVE_MISSION: dict[str, Any] | None = None


def build_execution_summary() -> dict[str, Any]:
    return {
        "status": "execution-foundation-ready",
        "active_mission": _ACTIVE_MISSION,
        "stages": STAGES,
        "governance": {
            "code_mutation": False,
            "branch_creation": False,
            "pull_request_creation": False,
            "merge": False,
            "deployment": False,
            "founder_approval_required": True,
        },
        "next_step": "Create an execution mission from a founder-approved request.",
    }


def create_execution_mission(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    if not authorized.get("authorized"):
        return {"status": "unauthorized", "authenticated": False}

    request = str(payload.get("founder_request") or payload.get("message") or "").strip()
    title = str(payload.get("title") or _title_from_request(request)).strip()

    if not request:
        return {"status": "missing-founder-request", "authenticated": True}

    now = _now()
    mission = {
        "mission_id": f"EXEC-{uuid4().hex[:8].upper()}",
        "title": title,
        "founder_request": request,
        "status": "approval-gated",
        "current_stage": STAGES[0],
        "stages": [_stage(name, name == STAGES[0]) for name in STAGES],
        "approval_required": True,
        "created_at": now,
        "updated_at": now,
        "next_recommended_action": "Generate Scope of Work and request founder approval before execution.",
    }

    global _ACTIVE_MISSION
    _ACTIVE_MISSION = mission
    return {"status": "execution-mission-created", "authenticated": True, "mission": mission}


def advance_execution_mission(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    if not authorized.get("authorized"):
        return {"status": "unauthorized", "authenticated": False}

    global _ACTIVE_MISSION
    if not _ACTIVE_MISSION:
        return {"status": "no-active-mission", "authenticated": True}

    current = str(payload.get("stage") or "").strip()
    if current and current not in STAGES:
        return {"status": "invalid-stage", "authenticated": True, "allowed_stages": STAGES}

    next_stage = current or _next_stage(str(_ACTIVE_MISSION.get("current_stage")))
    _ACTIVE_MISSION["current_stage"] = next_stage
    _ACTIVE_MISSION["updated_at"] = _now()
    _ACTIVE_MISSION["stages"] = [_stage(name, STAGES.index(name) <= STAGES.index(next_stage)) for name in STAGES]
    _ACTIVE_MISSION["next_recommended_action"] = _next_action(next_stage)

    return {"status": "execution-mission-advanced", "authenticated": True, "mission": _ACTIVE_MISSION}


def _stage(name: str, completed: bool) -> dict[str, Any]:
    return {"name": name, "label": name.replace("_", " ").title(), "completed": completed}


def _next_stage(current: str) -> str:
    if current not in STAGES:
        return STAGES[0]
    idx = min(STAGES.index(current) + 1, len(STAGES) - 1)
    return STAGES[idx]


def _next_action(stage: str) -> str:
    actions = {
        "intent_received": "Clarify requirements.",
        "requirements_clarified": "Generate Scope of Work.",
        "scope_of_work": "Run architecture review.",
        "architecture_review": "Generate implementation plan.",
        "implementation_plan": "Generate validation plan.",
        "validation_plan": "Request founder approval.",
        "founder_approval_required": "Founder approval required before execution.",
        "ready_for_execution": "Ready for future GitHub execution pipeline.",
    }
    return actions.get(stage, "Continue execution lifecycle.")


def _title_from_request(request: str) -> str:
    if not request:
        return "Execution Mission"
    words = request.split()
    return " ".join(words[:8]).strip().rstrip(".") or "Execution Mission"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
