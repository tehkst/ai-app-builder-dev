from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.platform.auth.service import require_founder


DEFAULT_VALIDATION = [
    "python -m compileall app/platform",
    "python -m app.platform.ui.login_module_boundary_check",
    "python -m app.platform.ui.ui_module_size_check",
    "dashboard render check",
    "JavaScript syntax check when UI changes",
]


def build_planning_summary() -> dict[str, Any]:
    return {
        "status": "planner-ready",
        "capability": "autonomous-engineering-planning",
        "mutation_enabled": False,
        "approval_required": True,
        "outputs": [
            "scope",
            "affected_files",
            "tasks",
            "risks",
            "validation_plan",
            "approval_package",
        ],
        "next_step": "Generate an engineering plan from a founder-approved mission.",
    }


def generate_engineering_plan(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    if not authorized.get("authorized"):
        return {"status": "unauthorized", "authenticated": False}

    request = str(payload.get("founder_request") or payload.get("message") or "").strip()
    mission_id = str(payload.get("mission_id") or "").strip()

    if not request:
        return {"status": "missing-founder-request", "authenticated": True}

    plan = {
        "plan_id": f"PLAN-{uuid4().hex[:8].upper()}",
        "mission_id": mission_id or None,
        "status": "planning-complete",
        "founder_request": request,
        "scope": _scope(request),
        "affected_files": _affected_files(request),
        "tasks": _tasks(request),
        "risks": _risks(request),
        "validation_plan": DEFAULT_VALIDATION,
        "approval_package": {
            "approval_required": True,
            "safe_to_execute": False,
            "reason": "Planner output only. Repository mutation is disabled until a future GitHub execution milestone.",
        },
        "created_at": _now(),
    }

    return {"status": "engineering-plan-created", "authenticated": True, "plan": plan}


def _scope(request: str) -> dict[str, Any]:
    return {
        "objective": request,
        "in_scope": [
            "Clarify implementation intent",
            "Identify likely files and modules",
            "Break work into safe execution tasks",
            "Define validation commands",
            "Prepare founder approval package",
        ],
        "out_of_scope": [
            "Code mutation",
            "Git branch creation",
            "Pull request creation",
            "Merge",
            "Production deployment",
        ],
    }


def _affected_files(request: str) -> list[str]:
    text = request.lower()
    files: list[str] = []

    if any(word in text for word in ["board", "chat", "conversation"]):
        files += [
            "app/platform/operating_console/service.py",
            "app/platform/ui/founder_dashboard_board_chat.py",
        ]
    if any(word in text for word in ["setting", "github", "provider", "dashboard", "ui"]):
        files += [
            "app/platform/ui/founder_dashboard_stable.py",
            "app/platform/ui/dashboard_browser_script.py",
        ]
    if any(word in text for word in ["execution", "mission", "planner", "plan"]):
        files += [
            "app/platform/execution/service.py",
            "app/platform/planning/service.py",
            "app/platform/server.py",
        ]

    return sorted(set(files or ["To be determined by repository inspection before execution."]))


def _tasks(request: str) -> list[dict[str, Any]]:
    return [
        {"step": 1, "title": "Confirm requirement", "description": "Restate founder request and acceptance criteria."},
        {"step": 2, "title": "Inspect architecture", "description": "Identify existing modules, boundaries, and reusable services."},
        {"step": 3, "title": "Prepare patch plan", "description": "List files to modify and expected behavior changes."},
        {"step": 4, "title": "Define validation", "description": "Select compile, boundary, render, and syntax checks."},
        {"step": 5, "title": "Request founder approval", "description": "Pause before any code mutation or GitHub execution."},
    ]


def _risks(request: str) -> list[str]:
    text = request.lower()
    risks = [
        "Scope may be too broad without founder confirmation.",
        "Existing dashboard HTML is highly compact and can be fragile to patch.",
    ]
    if any(word in text for word in ["auth", "login", "secret"]):
        risks.append("Auth or secret boundary changes require extra caution.")
    if any(word in text for word in ["deploy", "production", "traffic"]):
        risks.append("Deployment actions are explicitly out of scope for planner-only milestone.")
    return risks


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
