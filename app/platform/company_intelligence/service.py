from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from app.platform.ai_workforce.service import build_workforce_summary
from app.platform.auth.service import build_auth_summary
from app.platform.ci_repair.service import build_ci_repair_summary
from app.platform.code_planner.service import build_code_planner_summary, build_code_status
from app.platform.founder_approval.service import build_founder_approval_summary
from app.platform.founder_console.service import build_founder_console_summary
from app.platform.github_execution.service import build_github_execution_summary
from app.platform.knowledge_vault.service import build_knowledge_vault_summary
from app.platform.mission_control.service import build_mission_control_summary
from app.platform.operating_console.service import build_dashboard_state, build_operating_console_summary
from app.platform.pr_orchestration.service import build_gcp_handover_status, build_pr_orchestration_summary
from app.platform.repository_intelligence.service import build_repository_intelligence_summary
from app.platform.runtime.service import build_ai_provider_status, build_secret_manager_status

PRIMARY_REPOSITORY = "tehkst/ai-app-builder-dev"


def build_company_intelligence_snapshot() -> dict[str, Any]:
    mission_control = build_mission_control_summary()
    runtime = build_ai_provider_status()
    repository = build_repository_intelligence_summary()
    github = build_github_execution_summary()
    code = build_code_status()
    ci = build_ci_repair_summary()
    prs = build_pr_orchestration_summary()
    handover = build_gcp_handover_status()
    auth = build_auth_summary()
    secrets = build_secret_manager_status()
    return {
        "milestone": "INT-01",
        "status": "company-intelligence-ready",
        "generated_at": _now(),
        "company": "AI Software Factory",
        "primary_repository": PRIMARY_REPOSITORY,
        "environment": {
            "name": getattr(mission_control, "environment", "production"),
            "region": getattr(mission_control, "region", "asia-southeast1"),
            "cloud_run_service": os.getenv("K_SERVICE", "ai-software-factory-production"),
            "cloud_run_revision": os.getenv("K_REVISION", "unknown"),
        },
        "executive_summary": {
            "platform_stage": "approval-gated AI engineering operating system",
            "autonomy_level": "semi-autonomous",
            "estimated_completion_percent": 68,
            "primary_blockers": [
                "GitHub executor requires approved token or GitHub App installation",
                "Repository intelligence needs explicit primary repository binding in runtime outputs",
                "End-to-end request to proposal to execution to PR to deploy path needs live validation",
                "Company metrics and news feeds are UI-level placeholders until data integrations are added",
            ],
        },
        "capability_inventory": _capabilities(runtime, repository, github, code, ci, prs, handover, auth),
        "api_inventory": _api_inventory(),
        "subsystem_ownership": _ownership_matrix(),
        "workflow_model": _workflow_model(),
        "known_placeholders": _known_placeholders(),
        "security_guardrails": _security_guardrails(secrets),
        "board_room_context_policy": {
            "instruction": "Use this snapshot as authoritative platform context before executive discussion.",
            "avoid_language": ["appears", "not verifiable", "likely"],
            "required_behavior": "Distinguish known facts from unverified assumptions and ask for missing source access when needed.",
        },
        "raw_status": {
            "mission_control": _safe(mission_control),
            "founder_console": build_founder_console_summary(),
            "operating_console": build_operating_console_summary(),
            "dashboard": build_dashboard_state(),
            "workforce": build_workforce_summary(),
            "knowledge_vault": build_knowledge_vault_summary(),
            "repository": repository,
            "github_executor": github,
            "code_planner": build_code_planner_summary(),
            "code_status": code,
            "ci_repair": ci,
            "pull_requests": prs,
            "handover": handover,
            "approvals": build_founder_approval_summary(),
        },
    }


def build_company_intelligence_summary() -> dict[str, Any]:
    snapshot = build_company_intelligence_snapshot()
    return {
        "milestone": snapshot["milestone"],
        "status": snapshot["status"],
        "primary_repository": snapshot["primary_repository"],
        "environment": snapshot["environment"],
        "completion_percent": snapshot["executive_summary"]["estimated_completion_percent"],
        "capabilities": snapshot["capability_inventory"],
        "blockers": snapshot["executive_summary"]["primary_blockers"],
    }


def _capabilities(runtime: dict[str, Any], repository: dict[str, Any], github: dict[str, Any], code: dict[str, Any], ci: dict[str, Any], prs: dict[str, Any], handover: dict[str, Any], auth: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"name": "Founder authentication", "status": auth.get("status", "configured"), "owner": "Security"},
        {"name": "Mission Control UI", "status": "active", "owner": "Product"},
        {"name": "AI Board Room", "status": "active", "owner": "Executive Office"},
        {"name": "AI runtime", "status": runtime.get("status"), "owner": "Runtime"},
        {"name": "Repository intelligence", "status": repository.get("status"), "repository": PRIMARY_REPOSITORY, "owner": "Architecture"},
        {"name": "Code planner", "status": code.get("status"), "owner": "Engineering"},
        {"name": "GitHub executor", "status": github.get("status"), "owner": "DevOps"},
        {"name": "CI repair", "status": ci.get("status"), "owner": "QA"},
        {"name": "PR orchestration", "status": prs.get("status"), "owner": "DevOps"},
        {"name": "GCP handover", "status": handover.get("status"), "owner": "Cloud Runtime"},
    ]


def _api_inventory() -> list[dict[str, str]]:
    return [
        {"path": "/mission-control/operating-console/chat", "purpose": "Board Room chat through AI runtime"},
        {"path": "/mission-control/operating-console/workflow", "purpose": "Create proposal/workflow from discussion"},
        {"path": "/mission-control/repository/index", "purpose": "Repository indexing entry point"},
        {"path": "/mission-control/code/generate", "purpose": "Generate proposal-only code patch"},
        {"path": "/mission-control/code/validate", "purpose": "Validate generated proposal"},
        {"path": "/mission-control/github-executor/execute", "purpose": "Feature-branch GitHub execution"},
        {"path": "/mission-control/ci-repair/diagnose", "purpose": "Diagnose CI failures"},
        {"path": "/mission-control/handover", "purpose": "GCP handover readiness"},
    ]


def _ownership_matrix() -> dict[str, str]:
    return {
        "Founder intent": "Board Room / Operating Console",
        "Strategic discussion": "Board Room",
        "Implementation proposal": "Proposal Generator and Code Planner",
        "Repository truth": "Repository Intelligence",
        "Code mutation": "GitHub Executor only after approval",
        "Validation": "CI Repair and QA policy",
        "Deployment handover": "PR Orchestration and GCP Handover",
        "Security boundaries": "Founder Approval and Secret Manager",
    }


def _workflow_model() -> list[str]:
    return [
        "Founder command",
        "Company intelligence snapshot",
        "Board Room executive discussion",
        "Proposal generation",
        "Founder approval",
        "Repository context and file plan",
        "Code patch generation",
        "Validation",
        "Feature branch execution",
        "Pull request creation",
        "CI repair loop if needed",
        "Founder merge/deploy approval",
        "GCP handover",
    ]


def _known_placeholders() -> list[str]:
    return [
        "Revenue and customer metrics are demo placeholders until billing/customer integrations exist",
        "Company news is a placeholder until keyword news feeds are integrated",
        "AI employee activity is a UI representation until persistent job state is connected",
        "Repository intelligence is present but should expose explicit repository binding in every Board Room snapshot",
    ]


def _security_guardrails(secrets: dict[str, Any]) -> dict[str, Any]:
    return {
        "secret_manager_status": secrets.get("status"),
        "required": [
            "No direct commits to main",
            "Feature branch only execution",
            "Founder approval before mutation",
            "Least privilege GitHub token or GitHub App",
            "No secret values in prompts or logs",
            "CI repair retry limits",
            "Audit log for proposals, approvals, and execution",
        ],
    }


def _safe(value: Any) -> Any:
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return value


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
