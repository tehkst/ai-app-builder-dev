from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from app.platform.auth.service import build_auth_summary
from app.platform.ci_repair.service import build_ci_repair_summary
from app.platform.company_brain.service import build_company_brain_repository_summary
from app.platform.company_intelligence.service import build_company_intelligence_snapshot
from app.platform.github_execution.service import build_github_execution_summary
from app.platform.mission_control.service import build_mission_control_summary
from app.platform.pr_orchestration.service import build_gcp_handover_status, build_pr_orchestration_summary
from app.platform.repository_intelligence.service import build_repository_index, build_repository_intelligence_summary
from app.platform.runtime.service import build_ai_provider_status, build_persistent_runtime_summary, build_secret_manager_status

PRIMARY_REPOSITORY = "tehkst/ai-app-builder-dev"


def build_executive_intelligence_summary() -> dict[str, Any]:
    briefing = build_executive_intelligence_briefing()
    return {
        "company": briefing["company"],
        "product": briefing["product"],
        "milestone": briefing["milestone"],
        "status": briefing["status"],
        "generated_at": briefing["generated_at"],
        "primary_repository": briefing["primary_repository"],
        "environment": briefing["environment"],
        "readiness": briefing["readiness"],
        "board_room_context_policy": briefing["board_room_context_policy"],
        "recommended_next_action": briefing["recommended_next_action"],
    }


def build_executive_intelligence_briefing() -> dict[str, Any]:
    mission_control = _safe_call(build_mission_control_summary)
    runtime = _safe_call(build_persistent_runtime_summary)
    ai_provider = _safe_call(build_ai_provider_status)
    secrets = _safe_call(build_secret_manager_status)
    repository = _safe_call(build_repository_intelligence_summary)
    repository_index = _safe_call(build_repository_index, {"repository": PRIMARY_REPOSITORY})
    github = _safe_call(build_github_execution_summary)
    ci = _safe_call(build_ci_repair_summary)
    prs = _safe_call(build_pr_orchestration_summary)
    handover = _safe_call(build_gcp_handover_status)
    auth = _safe_call(build_auth_summary)
    company_brain = _safe_call(build_company_brain_repository_summary)
    legacy_snapshot = _safe_call(build_company_intelligence_snapshot)

    sources = {
        "mission_control": _source("Mission Control", "live-service", mission_control),
        "runtime": _source("GCP Runtime", "live-runtime-env", runtime),
        "ai_provider": _source("AI Provider", "live-runtime-env", ai_provider),
        "secret_manager": _source("Secret Manager Contract", "live-runtime-env", secrets),
        "repository": _source("Repository Intelligence", "runtime-service", repository),
        "repository_index": _source("Repository Index", "runtime-generated", repository_index),
        "github_executor": _source("GitHub Executor", "live-runtime-env", github),
        "ci_repair": _source("CI Repair", "runtime-service", ci),
        "pull_requests": _source("PR Orchestration", "runtime-service", prs),
        "gcp_handover": _source("GCP Handover", "runtime-service", handover),
        "auth": _source("Founder Auth", "runtime-service", auth),
        "company_brain": _source("Company Brain", "repository-backed", company_brain),
        "legacy_company_intelligence": _source("INT-01 Snapshot", "legacy-snapshot", legacy_snapshot),
    }

    readiness = _readiness(sources)
    return {
        "company": "AI Software Factory",
        "product": "Executive Intelligence Layer",
        "milestone": "AEL-01",
        "status": "executive-intelligence-ready",
        "generated_at": _now(),
        "primary_repository": PRIMARY_REPOSITORY,
        "purpose": "Give Board Room a fresh operational briefing assembled from live runtime services before planning or execution.",
        "environment": _environment(mission_control),
        "readiness": readiness,
        "executive_summary": _executive_summary(readiness, sources),
        "live_sources": sources,
        "architecture_signals": _architecture_signals(repository_index, sources),
        "operational_signals": _operational_signals(sources),
        "governance": _governance(github, secrets),
        "board_room_context_policy": {
            "instruction": "Use Executive Intelligence first. Treat INT-01 Company Intelligence as a legacy fallback, not the sole authority.",
            "required_behavior": [
                "Refresh live sources before producing implementation plans.",
                "Separate verified runtime facts from assumptions.",
                "Never claim GitHub write access unless runtime GitHub Executor reports token/configuration readiness.",
                "Never mutate GitHub without Founder approval and explicit live_execution=true.",
            ],
            "planning_order": [
                "Executive Intelligence",
                "Repository Intelligence",
                "Company Brain",
                "Board Room discussion",
                "Mission proposal",
                "Founder approval",
                "GitHub Executor",
            ],
        },
        "recommended_next_action": "Wire Board Room planning prompts to consume Executive Intelligence before using Company Intelligence fallback.",
    }


def _source(name: str, mode: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "mode": mode,
        "status": str(payload.get("status") or payload.get("state") or "available"),
        "freshness": "generated-on-request",
        "payload": payload,
    }


def _readiness(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    github_payload = sources["github_executor"]["payload"]
    ai_payload = sources["ai_provider"]["payload"]
    repo_payload = sources["repository"]["payload"]
    secrets_payload = sources["secret_manager"]["payload"]
    blocking = []
    if not github_payload.get("github_token_present"):
        blocking.append("GitHub Executor is not live-write ready until GITHUB_TOKEN is mounted in GCP Cloud Run.")
    if ai_payload.get("status") == "missing-secret":
        blocking.append("AI Provider is missing OPENAI_API_KEY in runtime configuration.")
    if repo_payload.get("status") != "repository-intelligence-ready":
        blocking.append("Repository Intelligence is not ready.")
    return {
        "status": "ready-with-blockers" if blocking else "ready",
        "autonomous_engineering_loop_ready": not blocking,
        "live_github_write_ready": bool(github_payload.get("github_token_present")),
        "ai_runtime_ready": ai_payload.get("status") == "configured",
        "repository_intelligence_ready": repo_payload.get("status") == "repository-intelligence-ready",
        "secret_manager_contract_ready": secrets_payload.get("status") == "secret-manager-contract-ready",
        "blocking_items": blocking,
    }


def _executive_summary(readiness: dict[str, Any], sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if readiness["autonomous_engineering_loop_ready"]:
        stage = "approval-gated autonomous engineering loop ready"
    else:
        stage = "approval-gated engineering loop partially ready"
    return {
        "platform_stage": stage,
        "primary_repository": PRIMARY_REPOSITORY,
        "live_source_count": len(sources),
        "blocking_items": readiness["blocking_items"],
        "top_risks": [
            "Board Room may still consume legacy INT-01 snapshots until planning prompts are rewired.",
            "Frontend remains fragile while large inline HTML/JS renderers exist.",
            "Live GitHub mutation must remain feature-branch only with Founder approval.",
        ],
    }


def _architecture_signals(repository_index: dict[str, Any], sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    areas = repository_index.get("areas") if isinstance(repository_index.get("areas"), list) else []
    return {
        "repository": PRIMARY_REPOSITORY,
        "indexed_area_count": len(areas),
        "indexed_areas": [area.get("area") for area in areas if isinstance(area, dict)],
        "critical_paths": _critical_paths(areas),
        "company_brain_status": sources["company_brain"]["status"],
    }


def _operational_signals(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "mission_control_status": sources["mission_control"]["status"],
        "runtime_status": sources["runtime"]["status"],
        "github_executor_status": sources["github_executor"]["status"],
        "ci_repair_status": sources["ci_repair"]["status"],
        "pr_orchestration_status": sources["pull_requests"]["status"],
        "gcp_handover_status": sources["gcp_handover"]["status"],
        "auth_status": sources["auth"]["status"],
    }


def _governance(github: dict[str, Any], secrets: dict[str, Any]) -> dict[str, Any]:
    safety = github.get("safety") if isinstance(github.get("safety"), dict) else {}
    return {
        "main_branch_write_allowed": bool(safety.get("main_branch_write_allowed", False)),
        "founder_approval_required": bool(safety.get("founder_approval_required", True)),
        "live_execution_requires_explicit_flag": bool(safety.get("live_execution_requires_explicit_flag", True)),
        "secrets_hidden": True,
        "secret_manager_status": secrets.get("status"),
        "merge_allowed_by_executor": False,
    }


def _critical_paths(areas: list[Any]) -> list[str]:
    paths: list[str] = []
    for area in areas:
        if not isinstance(area, dict):
            continue
        files = area.get("files") if isinstance(area.get("files"), list) else []
        paths.extend(str(path) for path in files)
    return sorted(set(paths))[:20]


def _environment(mission_control: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": mission_control.get("environment", os.getenv("AI_FACTORY_ENV", os.getenv("ENVIRONMENT", "production"))),
        "region": mission_control.get("region", os.getenv("GCP_REGION", "asia-southeast1")),
        "cloud_run_service": os.getenv("K_SERVICE", "ai-software-factory-production"),
        "cloud_run_revision": os.getenv("K_REVISION", "unknown"),
        "gcp_project_id": os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or "unknown",
    }


def _safe_call(func: Any, *args: Any) -> dict[str, Any]:
    try:
        value = func(*args)
    except Exception as exc:  # pragma: no cover - defensive runtime briefing boundary
        return {"status": "source-error", "error": str(exc), "source": getattr(func, "__name__", "unknown")}
    return _safe(value)


def _safe(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {"status": "available", "value": value}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
