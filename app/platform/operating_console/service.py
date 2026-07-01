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


def build_operating_console_summary() -> dict[str, Any]:
    ai = build_ai_provider_status()
    return {
        "company": "AI Software Factory",
        "product": "Founder Operating Console",
        "milestone": "GCP-P1",
        "status": "operating-console-ready",
        "mode": "gcp-primary-workflow-surface",
        "purpose": "Replace Swagger and ChatGPT as the day-to-day operating surface for founder-led autonomous software delivery.",
        "ai_provider": {
            "status": ai.get("status"),
            "model": ai.get("model"),
        },
        "dashboard": build_dashboard_state(),
        "endpoints": {
            "summary": "GET /mission-control/operating-console",
            "chat": "POST /mission-control/operating-console/chat",
            "workflow": "POST /mission-control/operating-console/workflow",
            "dashboard": "GET /mission-control/operating-console/dashboard",
        },
        "handover_status": "ready-for-gcp-primary-use-after-deploy-and-secret-setup",
    }


def build_dashboard_state() -> dict[str, Any]:
    approvals = build_founder_approval_summary()
    prs = build_pr_orchestration_summary()
    github = build_github_execution_summary()
    ci = build_ci_repair_summary()
    return {
        "tiles": [
            {"name": "Mission Chat", "status": "ready", "endpoint": "/mission-control/operating-console/chat"},
            {"name": "Approvals", "status": str(approvals.get("status", "ready")), "endpoint": "/mission-control/approvals"},
            {"name": "Pull Requests", "status": str(prs.get("status", "ready")), "endpoint": "/mission-control/pull-requests"},
            {"name": "GitHub Executor", "status": str(github.get("status", "ready")), "endpoint": "/mission-control/github-executor"},
            {"name": "CI Repair", "status": str(ci.get("status", "ready")), "endpoint": "/mission-control/ci-repair"},
        ],
        "queues": [
            {"queue": "new_founder_requests", "count": 0, "status": "ready-for-intake"},
            {"queue": "pending_approvals", "count": 0, "status": "ready"},
            {"queue": "engineering_prs", "count": 0, "status": "ready"},
            {"queue": "ci_failures", "count": 0, "status": "ready"},
        ],
        "logs": [
            {"time": _now(), "level": "info", "message": "Founder Operating Console ready."},
            {"time": _now(), "level": "info", "message": "Use Mission Chat to create and run work from GCP."},
        ],
    }


def chat_with_operating_console(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    message = str(payload.get("message") or payload.get("prompt") or "").strip()
    if not message:
        return {"status": "invalid-request", "error": "message is required"}

    mode = str(payload.get("mode") or "proposal").strip().lower()
    mission_id = str(payload.get("mission_id") or _id("MISSION", _now(), {"message": message}))
    system = (
        "You are the AI Software Factory Mission Control operator. "
        "Turn founder messages into concise execution-ready software missions. "
        "Return practical next steps, risks, validation gates, and founder approval notes."
    )
    ai_result = invoke_ai({"system": system, "prompt": message, "model": payload.get("model")})
    return {
        "company": "AI Software Factory",
        "product": "Founder Operating Console",
        "milestone": "GCP-P1",
        "status": "chat-response-ready" if ai_result.get("status") == "completed" else f"chat-{ai_result.get('status', 'unknown')}",
        "authorized": authorized.get("authorized", False),
        "role": authorized.get("role", "anonymous"),
        "mission_id": mission_id,
        "mode": mode,
        "message": message,
        "ai_response": ai_result,
        "workflow_hint": {
            "next_endpoint": "POST /mission-control/operating-console/workflow",
            "recommended_action": "create-proposal" if mode == "proposal" else "run-workflow",
        },
    }


def run_console_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    action = str(payload.get("action") or "create-proposal").strip().lower()
    request_text = str(payload.get("message") or payload.get("request") or payload.get("prompt") or "").strip()
    mission_id = str(payload.get("mission_id") or _id("MISSION", _now(), {"request": request_text, "action": action}))

    if not request_text:
        return {"status": "invalid-request", "error": "message/request is required"}

    intake = build_request_intake({"request": request_text, "mission_id": mission_id, "source": "operating-console"})
    proposal = generate_proposal({"request": request_text, "mission_id": mission_id, "title": payload.get("title") or request_text[:80]})
    result: dict[str, Any] = {
        "company": "AI Software Factory",
        "product": "Founder Operating Console",
        "milestone": "GCP-P1",
        "status": "workflow-created",
        "authorized": authorized.get("authorized", False),
        "role": authorized.get("role", "anonymous"),
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
