from __future__ import annotations

from typing import Any

from app.platform.autonomous_engineering.service import build_autonomous_engineering_summary
from app.platform.code_planner.service import build_code_status
from app.platform.founder_approval.service import build_founder_approval_summary
from app.platform.founder_workspace.service import build_founder_workspace_summary
from app.platform.mission_execution.service import build_mission_execution_summary
from app.platform.patch_application.service import build_patch_application_summary
from app.platform.pr_orchestration.service import build_gcp_handover_status, build_pr_orchestration_summary
from app.platform.proposal_generator.service import build_proposal_generator_summary
from app.platform.repository_intelligence.service import build_repository_intelligence_summary
from app.platform.runtime.service import build_ai_provider_status, build_persistent_runtime_summary


def build_founder_console_summary() -> dict[str, Any]:
    runtime = build_persistent_runtime_summary()
    ai_provider = build_ai_provider_status()
    handover = build_gcp_handover_status()
    return {
        "company": "AI Software Factory",
        "product": "Founder Mission Control UI",
        "milestone": "GCP-13",
        "status": "founder-console-ready",
        "mode": "dashboard-and-action-console",
        "login_status": "pending-gcp-identity-integration",
        "mission_control_primary_workflow": handover.get("can_move_primary_workflow_to_gcp", False),
        "runtime": {
            "status": runtime.get("status"),
            "ai_provider": ai_provider.get("status"),
            "model": ai_provider.get("model"),
        },
        "console_sections": build_console_sections(),
        "action_queues": build_action_queues(),
        "next_step": "GCP-14 GitHub Write Executor and authenticated founder actions.",
    }


def build_console_sections() -> list[dict[str, str]]:
    return [
        {
            "section": "Founder Intake",
            "purpose": "Capture founder requests and turn them into proposals.",
            "primary_endpoint": "POST /mission-control/requests",
            "ui_state": "ready",
        },
        {
            "section": "Proposal Inbox",
            "purpose": "Generate, inspect, approve, or reject proposals.",
            "primary_endpoint": "POST /mission-control/proposals/generate",
            "ui_state": "ready",
        },
        {
            "section": "Mission Queue",
            "purpose": "Plan and start approved engineering missions.",
            "primary_endpoint": "POST /mission-control/missions/plan",
            "ui_state": "ready",
        },
        {
            "section": "Engineering Worker",
            "purpose": "Create blueprints, PR plans, repository context, and code proposals.",
            "primary_endpoint": "POST /mission-control/engineering-worker/blueprint",
            "ui_state": "ready",
        },
        {
            "section": "Code & Patch Queue",
            "purpose": "Validate, package, prepare, and apply approved patches.",
            "primary_endpoint": "POST /mission-control/code/generate",
            "ui_state": "ready",
        },
        {
            "section": "Pull Request Queue",
            "purpose": "Prepare PR creation records and track review status.",
            "primary_endpoint": "POST /mission-control/pull-requests/prepare",
            "ui_state": "ready",
        },
        {
            "section": "Runtime Monitor",
            "purpose": "Check AI provider, Secret Manager, runtime, and handover health.",
            "primary_endpoint": "GET /mission-control/runtime",
            "ui_state": "ready",
        },
    ]


def build_action_queues() -> list[dict[str, Any]]:
    proposals = build_proposal_generator_summary()
    approvals = build_founder_approval_summary()
    missions = build_mission_execution_summary()
    repository = build_repository_intelligence_summary()
    engineering = build_autonomous_engineering_summary()
    code = build_code_status()
    patches = build_patch_application_summary()
    prs = build_pr_orchestration_summary()
    workspace = build_founder_workspace_summary()
    return [
        _queue("Founder Requests", workspace.get("status"), "Open or submit a founder request", "/mission-control/founder"),
        _queue("Proposals", proposals.get("status"), "Generate proposal from request", "/mission-control/proposals"),
        _queue("Approvals", approvals.get("status"), "Approve or reject generated proposal", "/mission-control/approvals"),
        _queue("Missions", missions.get("status"), "Plan and start mission", "/mission-control/missions"),
        _queue("Repository", repository.get("status"), "Create repository context and file plan", "/mission-control/repository"),
        _queue("Engineering", engineering.get("status"), "Create blueprint or PR plan", "/mission-control/engineering-worker"),
        _queue("Code", code.get("status"), "Generate, validate, and package patch proposal", "/mission-control/code"),
        _queue("Patches", patches.get("status"), "Prepare patch application", "/mission-control/patches"),
        _queue("Pull Requests", prs.get("status"), "Prepare PR creation record", "/mission-control/pull-requests"),
    ]


def _queue(name: str, status: Any, action: str, endpoint: str) -> dict[str, str]:
    return {
        "name": name,
        "status": str(status or "ready"),
        "action": action,
        "endpoint": endpoint,
    }
