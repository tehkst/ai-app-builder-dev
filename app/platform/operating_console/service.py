from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.platform.auth.service import require_founder
from app.platform.ci_repair.service import build_ci_repair_summary
from app.platform.founder_approval.service import approve_proposal, build_founder_approval_summary
from app.platform.founder_workspace.service import build_request_intake
from app.platform.github_execution.service import build_github_execution_summary
from app.platform.mission_execution.service import plan_mission, start_mission
from app.platform.pr_orchestration.service import build_pr_orchestration_summary
from app.platform.proposal_generator.service import generate_proposal
from app.platform.runtime.service import build_ai_provider_status, invoke_ai


BOARD_ROOM_ROLES = [
    "Founder",
    "AI CEO",
    "AI CTO",
    "Engineering Manager",
    "Senior Engineer",
    "QA Lead",
    "DevOps Lead",
    "Product Manager",
]


def build_operating_console_summary() -> dict[str, Any]:
    ai = build_ai_provider_status()
    return {
        "company": "AI Software Factory",
        "product": "Founder Operating Console",
        "milestone": "ADMIN-01",
        "status": "admin-console-ready",
        "mode": "login-first-board-room",
        "purpose": "Give the founder a proper GCP Platform Admin login and Board Room chat entry point before consolidation work begins.",
        "ai_provider": {
            "status": ai.get("status"),
            "model": ai.get("model"),
        },
        "dashboard": build_dashboard_state(),
        "board_room": build_board_room_state(),
        "endpoints": {
            "summary": "GET /mission-control/operating-console",
            "dashboard": "GET /mission-control/operating-console/dashboard",
            "chat": "POST /mission-control/operating-console/chat",
            "workflow": "POST /mission-control/operating-console/workflow",
            "board_room_chat": "POST /mission-control/board-room/chat",
        },
        "handover_status": "ready-for-founder-login-and-board-room-use-after-deploy-and-secret-setup",
    }


def build_dashboard_state() -> dict[str, Any]:
    approvals = build_founder_approval_summary()
    prs = build_pr_orchestration_summary()
    github = build_github_execution_summary()
    ci = build_ci_repair_summary()
    return {
        "tiles": [
            {"name": "Board Room", "status": "ready", "endpoint": "/mission-control/board-room/chat"},
            {"name": "Approvals", "status": str(approvals.get("status", "ready")), "endpoint": "/mission-control/approvals"},
            {"name": "Pull Requests", "status": str(prs.get("status", "ready")), "endpoint": "/mission-control/pull-requests"},
            {"name": "GitHub Executor", "status": str(github.get("status", "ready")), "endpoint": "/mission-control/github-executor"},
            {"name": "CI Repair", "status": str(ci.get("status", "ready")), "endpoint": "/mission-control/ci-repair"},
        ],
        "queues": [
            {"queue": "board_room_topics", "count": 0, "status": "ready-for-founder"},
            {"queue": "pending_approvals", "count": 0, "status": "ready"},
            {"queue": "engineering_prs", "count": 0, "status": "ready"},
            {"queue": "ci_failures", "count": 0, "status": "ready"},
        ],
        "logs": [
            {"time": _now(), "level": "info", "message": "Admin login and Board Room are ready."},
            {"time": _now(), "level": "info", "message": "Use Board Room to direct consolidation and cleanup missions."},
        ],
    }


def build_board_room_state() -> dict[str, Any]:
    return {
        "status": "board-room-ready",
        "roles": BOARD_ROOM_ROLES,
        "default_agenda": [
            "Clarify founder intent",
            "Identify existing capabilities before building new ones",
            "Recommend reuse or consolidation",
            "Create proposal only after architectural review",
            "Keep all execution behind founder approval",
        ],
        "primary_endpoint": "POST /mission-control/board-room/chat",
    }


def board_room_chat(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    if not authorized.get("authorized"):
        return {
            "status": "unauthorized",
            "authenticated": False,
            "message": "Please login to Mission Control before entering the Board Room.",
        }

    message = str(payload.get("message") or payload.get("prompt") or "").strip()
    if not message:
        return {"status": "invalid-request", "error": "message is required"}

    agenda = payload.get("agenda") or build_board_room_state()["default_agenda"]
    system = (
        "You are the AI Software Factory Board Room: AI CEO, AI CTO, Product Manager, Engineering Manager, "
        "Senior Engineer, QA Lead, DevOps Lead, and Security Advisor. Your job is to help the founder run the company from GCP Mission Control. "
        "Before recommending new code, check whether capability likely already exists, call out possible overlap, and propose consolidation-first actions. "
        "Return a board-room decision with: executive summary, existing capability check, recommendation, risks, approval gates, and next action."
    )
    prompt = f"Founder message: {message}\n\nBoard agenda: {json.dumps(agenda)}"
    ai_result = invoke_ai({"system": system, "prompt": prompt, "model": payload.get("model")})
    meeting_id = str(payload.get("meeting_id") or _id("BOARD", _now(), {"message": message}))
    return {
        "company": "AI Software Factory",
        "product": "Mission Control Board Room",
        "milestone": "ADMIN-01",
        "status": "board-room-response-ready" if ai_result.get("status") == "completed" else f"board-room-{ai_result.get('status', 'unknown')}",
        "authenticated": True,
        "meeting_id": meeting_id,
        "participants": BOARD_ROOM_ROLES,
        "founder_message": message,
        "ai_response": ai_result,
        "next_step": "Use the Board Room decision to create a consolidation or cleanup proposal.",
    }


def chat_with_operating_console(payload: dict[str, Any]) -> dict[str, Any]:
    return board_room_chat(payload)


def run_console_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    if not authorized.get("authorized"):
        return {
            "status": "unauthorized",
            "authenticated": False,
            "message": "Please login to Mission Control before running workflows.",
        }

    action = str(payload.get("action") or "create-proposal").strip().lower()
    request_text = str(payload.get("message") or payload.get("request") or payload.get("prompt") or "").strip()
    mission_id = str(payload.get("mission_id") or _id("MISSION", _now(), {"request": request_text, "action": action}))

    if not request_text:
        return {"status": "invalid-request", "error": "message/request is required"}

    intake = build_request_intake({"request": request_text, "mission_id": mission_id, "source": "board-room"})
    proposal = generate_proposal({"request": request_text, "mission_id": mission_id, "title": payload.get("title") or request_text[:80]})
    result: dict[str, Any] = {
        "company": "AI Software Factory",
        "product": "Founder Operating Console",
        "milestone": "ADMIN-01",
        "status": "workflow-created",
        "authenticated": True,
        "role": authorized.get("role", "founder"),
        "action": action,
        "mission_id": mission_id,
        "intake": intake,
        "proposal": proposal,
        "next_step": "Review the proposal in Mission Control and approve before execution.",
    }

    if action in {"approve", "approve-and-plan", "approve-and-start"}:
        approval = approve_proposal(
            {
                "proposal_id": proposal.get("proposal", {}).get("proposal_id") or payload.get("proposal_id") or mission_id,
                "approved_by": authorized.get("email") or payload.get("approved_by") or "founder",
                "approval_notes": "Approved from Founder Operating Console.",
            }
        )
        result["approval"] = approval
        result["status"] = "workflow-approved"
        result["next_step"] = "Plan the approved mission."

    if action in {"approve-and-plan", "approve-and-start", "plan"}:
        plan = plan_mission({"mission_id": mission_id, "title": payload.get("title") or request_text[:80], "goal": request_text})
        result["mission_plan"] = plan
        result["status"] = "workflow-planned"
        result["next_step"] = "Start the mission when ready."

    if action in {"approve-and-start", "start"}:
        started = start_mission({"mission_id": mission_id, "title": payload.get("title") or request_text[:80], "goal": request_text})
        result["mission_start"] = started
        result["status"] = "workflow-started"
        result["next_step"] = "Use repository intelligence, code generation, GitHub executor, and CI repair queues from the dashboard."

    return result


def _id(prefix: str, timestamp: str, data: Any) -> str:
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}-{timestamp[:10].replace('-', '')}-{digest}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
