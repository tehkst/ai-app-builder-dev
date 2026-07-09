from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.platform.auth.service import require_founder


GOVERNANCE = {
    "mutation_enabled": False,
    "branch_creation": False,
    "pr_creation": False,
    "deployment": False,
    "founder_approval_required": True,
}


def build_engineering_manager_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Engineering Manager",
        "milestone": "MC-ENG-01",
        "status": "engineering-manager-ready",
        "mode": "planning-management-only",
        "endpoints": {
            "summary": "GET /mission-control/engineering-manager",
            "breakdown": "POST /mission-control/engineering-manager/breakdown",
        },
        "outputs": [
            "epic",
            "user_stories",
            "engineering_tasks",
            "dependency_order",
            "acceptance_criteria",
            "validation_plan",
            "rollback_plan",
            "approval_package",
        ],
        "governance": GOVERNANCE,
        "next_step": "Generate an execution-ready engineering breakdown from a planner output or founder request.",
    }


def create_engineering_breakdown(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    if not authorized.get("authorized"):
        return {"status": "unauthorized", "authenticated": False}

    source = _source(payload)
    founder_request = source["founder_request"]
    if not founder_request:
        return {"status": "missing-founder-request", "authenticated": True}

    created_at = _now()
    mission_id = source["mission_id"] or _id("MISSION", created_at, {"request": founder_request})
    breakdown_id = _id("EM", created_at, {"mission_id": mission_id, "request": founder_request})
    tasks = _engineering_tasks(founder_request)
    criteria = _acceptance_criteria(source, founder_request)
    breakdown = {
        "breakdown_id": breakdown_id,
        "mission_id": mission_id,
        "founder_request": founder_request,
        "epic": _epic(founder_request),
        "user_stories": _user_stories(founder_request),
        "engineering_tasks": tasks,
        "dependency_order": [task["task_id"] for task in tasks],
        "acceptance_criteria": criteria,
        "validation_plan": _validation_plan(source),
        "rollback_plan": _rollback_plan(),
        "approval_package": _approval_package(mission_id, breakdown_id, criteria),
        "created_at": created_at,
    }
    return {"status": "engineering-breakdown-created", "authenticated": True, **breakdown}


def _source(payload: dict[str, Any]) -> dict[str, Any]:
    planner = payload.get("planner_output") if isinstance(payload.get("planner_output"), dict) else {}
    plan = planner.get("plan") if isinstance(planner.get("plan"), dict) else planner
    scope = plan.get("scope") if isinstance(plan.get("scope"), dict) else {}
    request = str(payload.get("founder_request") or payload.get("message") or plan.get("founder_request") or scope.get("objective") or "").strip()
    mission_id = str(payload.get("mission_id") or plan.get("mission_id") or "").strip()
    acceptance = payload.get("acceptance_criteria") or plan.get("acceptance_criteria") or []
    validation = payload.get("validation_plan") or plan.get("validation_plan") or []
    return {
        "founder_request": request,
        "mission_id": mission_id,
        "acceptance_criteria": acceptance,
        "validation_plan": validation,
    }


def _epic(request: str) -> dict[str, str]:
    return {
        "title": _title(request),
        "objective": request,
        "management_note": "Breakdown is execution-ready planning only. No repository mutation is authorized.",
    }


def _user_stories(request: str) -> list[dict[str, str]]:
    return [
        {"story_id": "US-1", "role": "Founder", "story": f"As founder, I want {request} to be broken into safe engineering work.", "value": "Clear reviewable execution plan."},
        {"story_id": "US-2", "role": "Engineering Manager", "story": "As Engineering Manager, I want ordered tasks and validation gates.", "value": "Engineers can execute after approval without ambiguity."},
        {"story_id": "US-3", "role": "QA Lead", "story": "As QA Lead, I want acceptance criteria and rollback expectations.", "value": "Validation is explicit before any merge or deployment."},
    ]


def _engineering_tasks(request: str) -> list[dict[str, Any]]:
    return [
        {"task_id": "TASK-1", "owner": "Engineering Manager", "title": "Confirm scope and constraints", "description": f"Restate the founder request and confirm out-of-scope mutation boundaries: {request}", "depends_on": []},
        {"task_id": "TASK-2", "owner": "AI CTO", "title": "Map affected architecture", "description": "Identify services, UI surfaces, endpoint contracts, and governance boundaries before implementation.", "depends_on": ["TASK-1"]},
        {"task_id": "TASK-3", "owner": "Senior Engineer", "title": "Prepare implementation task list", "description": "Translate the approved plan into small file-level work items without generating patches.", "depends_on": ["TASK-2"]},
        {"task_id": "TASK-4", "owner": "QA Lead", "title": "Define validation gates", "description": "Select compile, module boundary, render, and JavaScript checks required before approval.", "depends_on": ["TASK-3"]},
        {"task_id": "TASK-5", "owner": "DevOps Lead", "title": "Confirm rollback and release safety", "description": "Document rollback path and confirm no deployment action is authorized by this breakdown.", "depends_on": ["TASK-4"]},
        {"task_id": "TASK-6", "owner": "Founder", "title": "Review approval package", "description": "Approve or revise the breakdown before any code, branch, PR, merge, or deployment action.", "depends_on": ["TASK-5"]},
    ]


def _acceptance_criteria(source: dict[str, Any], request: str) -> list[str]:
    raw = source.get("acceptance_criteria")
    if isinstance(raw, str):
        items = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
    elif isinstance(raw, list):
        items = [str(item).strip() for item in raw if str(item).strip()]
    else:
        items = []
    return items or [
        "Engineering breakdown includes ordered tasks, owners, dependencies, validation, rollback, and approval package.",
        "No code patches, branch creation, pull request creation, merge, or deployment is performed.",
        f"Founder request is traceable in the breakdown: {request}",
    ]


def _validation_plan(source: dict[str, Any]) -> list[str]:
    raw = source.get("validation_plan")
    if isinstance(raw, list) and raw:
        return [str(item).strip() for item in raw if str(item).strip()]
    return [
        "python -m compileall app/platform",
        "python -m app.platform.ui.login_module_boundary_check",
        "python -m app.platform.ui.ui_module_size_check",
        "Dashboard render check",
        "node --check generated dashboard JS",
    ]


def _rollback_plan() -> list[str]:
    return [
        "No repository mutation is performed by Engineering Manager.",
        "If the breakdown is wrong, discard it and regenerate after founder clarification.",
        "If later execution fails, revert only the future approved implementation PR; this milestone creates no branch or deployment state.",
    ]


def _approval_package(mission_id: str, breakdown_id: str, criteria: list[str]) -> dict[str, Any]:
    return {
        "mission_id": mission_id,
        "breakdown_id": breakdown_id,
        "approval_required": True,
        "safe_to_execute": False,
        "governance": GOVERNANCE,
        "review_checklist": criteria,
        "approval_note": "Founder approval is required before any implementation, branch, PR, merge, or deployment.",
    }


def _title(request: str) -> str:
    words = " ".join(request.split())[:80]
    return words or "Engineering Breakdown"


def _id(prefix: str, timestamp: str, data: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}-{timestamp[:10].replace('-', '')}-{digest}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
