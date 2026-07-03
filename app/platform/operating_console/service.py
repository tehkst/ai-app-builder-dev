from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.platform.auth.service import require_founder
from app.platform.ci_repair.service import build_ci_repair_summary
from app.platform.code_planner.service import build_code_status
from app.platform.company_intelligence.service import build_company_intelligence_snapshot
from app.platform.conversation_intelligence.service import analyze_conversation
from app.platform.founder_approval.service import approve_proposal, build_founder_approval_summary
from app.platform.founder_workflow.service import build_workflow_from_console_result
from app.platform.founder_workspace.service import build_request_intake
from app.platform.github_execution.service import build_github_execution_summary
from app.platform.mission_execution.service import plan_mission, start_mission
from app.platform.pr_orchestration.service import build_gcp_handover_status, build_pr_orchestration_summary
from app.platform.proposal_generator.service import generate_proposal
from app.platform.repository_intelligence.service import build_repository_intelligence_summary
from app.platform.runtime.service import build_ai_provider_status, invoke_ai


BOARD_ROOM_ROLES = ["Founder", "AI CEO", "AI CTO", "Engineering Manager", "Senior Engineer", "QA Lead", "DevOps Lead", "Product Manager"]


def build_operating_console_summary() -> dict[str, Any]:
    ai = build_ai_provider_status()
    return {
        "company": "AI Software Factory",
        "product": "Founder Operating Console",
        "milestone": "INT-01",
        "status": "company-intelligence-board-room-ready",
        "mode": "login-first-ai-board-room",
        "purpose": "Give the founder a Board Room that reasons from a company intelligence snapshot before making recommendations.",
        "ai_provider": {"status": ai.get("status"), "model": ai.get("model")},
        "dashboard": build_dashboard_state(),
        "board_room": build_board_room_state(),
        "endpoints": {"summary": "GET /mission-control/operating-console", "dashboard": "GET /mission-control/operating-console/dashboard", "chat": "POST /mission-control/operating-console/chat", "workflow": "POST /mission-control/operating-console/workflow", "company_intelligence": "GET /mission-control/company-intelligence"},
        "handover_status": "ready-for-company-intelligence-board-room-discussions",
    }


def build_dashboard_state() -> dict[str, Any]:
    approvals = build_founder_approval_summary()
    prs = build_pr_orchestration_summary()
    github = build_github_execution_summary()
    ci = build_ci_repair_summary()
    return {
        "tiles": [
            {"name": "Board Room", "status": "company-intelligence-ready", "endpoint": "/mission-control/operating-console/chat"},
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
        "logs": [{"time": _now(), "level": "info", "message": "AI Board Room is ready."}, {"time": _now(), "level": "info", "message": "Company Intelligence snapshot is injected into Board Room prompts."}],
    }


def build_board_room_state() -> dict[str, Any]:
    return {
        "status": "company-intelligence-board-room-ready",
        "roles": BOARD_ROOM_ROLES,
        "default_agenda": ["Clarify founder intent", "Review Company Intelligence snapshot before opinions", "Identify existing capabilities before building new ones", "Separate known facts from unverified assumptions", "Recommend reuse or consolidation", "Create proposal only after architectural review", "Keep all execution behind founder approval"],
        "primary_endpoint": "POST /mission-control/operating-console/chat",
    }


def board_room_chat(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    if not authorized.get("authorized"):
        return {"status": "unauthorized", "authenticated": False, "message": "Please login to Mission Control before entering the Board Room."}
    message = str(payload.get("message") or payload.get("prompt") or "").strip()
    if not message:
        return {"status": "invalid-request", "error": "message is required"}
    meeting_id = str(payload.get("meeting_id") or _id("BOARD", _now(), {"message": message}))
    context = _board_room_context()
    agenda = payload.get("agenda") or build_board_room_state()["default_agenda"]
    ai_result = invoke_ai({"system": _board_room_system_prompt(), "prompt": _board_room_prompt(message=message, agenda=agenda, context=context), "model": payload.get("model")})
    output_text = str(ai_result.get("output_text") or "").strip()
    intelligence = analyze_conversation({"message": message, "board_room_response": output_text}).get("conversation_intelligence", {})
    return {
        "company": "AI Software Factory",
        "product": "Mission Control AI Board Room",
        "milestone": "INT-01",
        "status": "board-room-response-ready" if ai_result.get("status") == "completed" else f"board-room-{ai_result.get('status', 'unknown')}",
        "authenticated": True,
        "meeting_id": meeting_id,
        "participants": BOARD_ROOM_ROLES,
        "founder_message": message,
        "board_room_response": output_text or _fallback_board_response(ai_result),
        "conversation_intelligence": intelligence,
        "ai_response": ai_result,
        "context_snapshot": context,
        "governance": {"execution_allowed": False, "proposal_required_before_execution": True, "founder_approval_required": True, "company_intelligence_required": True},
        "next_step": str(intelligence.get("recommended_next_action") or "Review the Board Room response. Generate a workflow only when you want to convert the discussion into an approval-gated workflow."),
    }


def chat_with_operating_console(payload: dict[str, Any]) -> dict[str, Any]:
    return board_room_chat(payload)


def run_console_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    if not authorized.get("authorized"):
        return {"status": "unauthorized", "authenticated": False, "message": "Please login to Mission Control before running workflows."}
    action = str(payload.get("action") or "create-proposal").strip().lower()
    request_text = str(payload.get("message") or payload.get("request") or payload.get("prompt") or "").strip()
    mission_id = str(payload.get("mission_id") or _id("MISSION", _now(), {"request": request_text, "action": action}))
    if not request_text:
        return {"status": "invalid-request", "error": "message/request is required"}
    intelligence = analyze_conversation({"message": request_text}).get("conversation_intelligence", {})
    intake = build_request_intake({"request": request_text, "mission_id": mission_id, "source": "board-room"})
    proposal = _roadmap_proposal_record(intelligence, mission_id, request_text) if intelligence.get("workflow_type") == "roadmap" else generate_proposal({"request": request_text, "mission_id": mission_id, "title": payload.get("title") or request_text[:80]})
    result: dict[str, Any] = {"company": "AI Software Factory", "product": "Founder Operating Console", "milestone": "INT-01", "status": "workflow-created", "authenticated": True, "role": authorized.get("role", "founder"), "action": action, "mission_id": mission_id, "intake": intake, "proposal": proposal, "conversation_intelligence": intelligence, "company_intelligence": build_company_intelligence_snapshot(), "next_step": str(intelligence.get("recommended_next_action") or "Review the proposal in Mission Control and approve before execution.")}
    if action in {"approve", "approve-and-plan", "approve-and-start"}:
        approval = approve_proposal({"proposal_id": proposal.get("proposal", {}).get("proposal_id") or payload.get("proposal_id") or mission_id, "approved_by": authorized.get("email") or payload.get("approved_by") or "founder", "approval_notes": "Approved from Founder Operating Console."})
        result["approval"] = approval
        result["status"] = "workflow-approved"
        result["next_step"] = "Select the first roadmap mission." if intelligence.get("workflow_type") == "roadmap" else "Plan the approved mission."
    if action in {"approve-and-plan", "approve-and-start", "plan"} and intelligence.get("workflow_type") != "roadmap":
        plan = plan_mission({"mission_id": mission_id, "title": payload.get("title") or request_text[:80], "goal": request_text})
        result["mission_plan"] = plan
        result["status"] = "workflow-planned"
        result["next_step"] = "Start the mission when ready."
    if action in {"approve-and-start", "start"} and intelligence.get("workflow_type") != "roadmap":
        started = start_mission({"mission_id": mission_id, "title": payload.get("title") or request_text[:80], "goal": request_text})
        result["mission_start"] = started
        result["status"] = "workflow-started"
        result["next_step"] = "Use repository intelligence, code generation, GitHub executor, and CI repair queues from the dashboard."
    result["founder_workflow"] = build_workflow_from_console_result(result, request_text)
    return result


def _roadmap_proposal_record(intelligence: dict[str, Any], mission_id: str, request_text: str) -> dict[str, Any]:
    roadmap = intelligence.get("roadmap_proposal") if isinstance(intelligence.get("roadmap_proposal"), dict) else {}
    return {
        "company": "AI Software Factory",
        "product": "Roadmap Proposal Generator",
        "status": "roadmap-generated-for-founder-review",
        "proposal_id": f"ROADMAP-{mission_id}",
        "proposal": {
            "proposal_id": f"ROADMAP-{mission_id}",
            "title": roadmap.get("title") or "Mission Control Engineering Roadmap",
            "status": "generated",
            "executive_summary": "Prioritized mission roadmap generated from Board Room discussion. Approval authorizes planning only, not implementation.",
            "business_objective": request_text,
            "recommended_solution": "Review and approve the roadmap, then select a single mission for implementation planning.",
            "roadmap": roadmap,
            "acceptance_criteria": ["Roadmap is visible for Founder review.", "No implementation begins from roadmap approval alone."],
        },
        "next_step": "Founder reviews roadmap and selects a mission for separate implementation approval.",
    }


def _board_room_context() -> dict[str, Any]:
    return build_company_intelligence_snapshot()


def _board_room_system_prompt() -> str:
    return "You are the AI Software Factory Board Room inside the founder's GCP Mission Control platform. Use the supplied Company Intelligence snapshot as authoritative platform context. Separate known facts from assumptions. Audit before building, reuse before creating, consolidate before expanding. Never claim execution. Return clear board-room sections."


def _board_room_prompt(*, message: str, agenda: Any, context: dict[str, Any]) -> str:
    return f"""
Founder message:
{message}

Board agenda:
{json.dumps(agenda, indent=2)}

Company Intelligence snapshot:
{json.dumps(context, indent=2, sort_keys=True, default=str)}

Respond with these sections:
1. Executive Summary
2. Known Company Facts From Intelligence Snapshot
3. Board Discussion
4. Existing Capability / Overlap Check
5. Recommendation
6. Risks and Guardrails
7. Founder Decision Required
8. Next Action
""".strip()


def _fallback_board_response(ai_result: dict[str, Any]) -> str:
    return f"Board Room could not complete AI response. Status: {ai_result.get('status', 'unknown')}. Detail: {ai_result.get('error') or 'No AI output was returned.'}"


def _id(prefix: str, timestamp: str, data: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}-{timestamp[:10].replace('-', '')}-{digest}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
