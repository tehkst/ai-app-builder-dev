from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.platform.capability_intelligence.service import get_capability_intelligence_status
from app.platform.health.health_status import build_health_status
from app.platform.pipeline.mission_pipeline import build_mission_pipeline_summary

PRIMARY_REPOSITORY = "tehkst/ai-app-builder-dev"
REPO_ROOT = Path(__file__).resolve().parents[3]
UNKNOWN = "unknown"


def build_executive_intelligence_summary() -> Dict[str, Any]:
    snapshot = build_executive_intelligence_briefing()
    return {
        "company": snapshot["company"],
        "product": snapshot["product"],
        "milestone": snapshot["milestone"],
        "status": snapshot["status"],
        "generated_at": snapshot["generated_at"],
        "primary_repository": snapshot["repository_identity"]["value"],
        "repository_identity": snapshot["repository_identity"],
        "platform_health": snapshot["platform_health"],
        "blockers": snapshot["blockers"],
        "next_recommended_action": snapshot["next_recommended_action"],
        "governance": snapshot["governance"],
    }


def build_executive_intelligence_briefing(
    source_overrides: Optional[Dict[str, Callable[[], Any]]] = None,
) -> Dict[str, Any]:
    generated_at = _now()
    collectors = {
        "repository": _repository_state,
        "missions": build_mission_pipeline_summary,
        "capabilities": get_capability_intelligence_status,
        "github": _github_state,
        "deployment": _deployment_state,
        "verification": _verification_state,
        "health": build_health_status,
        "sprint": _sprint_state,
        "release": _release_state,
    }
    collectors.update(source_overrides or {})
    sources = {
        name: _collect(name, collector, generated_at)
        for name, collector in collectors.items()
    }
    repository = _repository_claims(sources["repository"], generated_at)
    mission = _mission_claims(sources["missions"], generated_at)
    github = _github_claims(sources["github"], generated_at)
    deployment = _deployment_claims(sources["deployment"], generated_at)
    verification = _claim_from_source(sources["verification"], "production_verification", generated_at)
    health = _health_claim(sources["health"], generated_at)
    sprint = _claim_from_source(sources["sprint"], "current_sprint", generated_at)
    release = _claim_from_source(sources["release"], "release_stage", generated_at)
    blockers = _derive_blockers(sources, mission, github, deployment, verification, health, generated_at)
    risks = _derive_risks(sources, repository, github, deployment, generated_at)
    next_action = _derive_next_action(mission, github, deployment, verification, blockers, generated_at)
    return {
        "company": "AI Software Factory",
        "product": "Executive Intelligence Layer",
        "milestone": "SPRINT-2-P0-EXECUTIVE-BRAIN-LIVE",
        "status": "executive-state-ready",
        "generated_at": generated_at,
        "state_contract_version": "executive-state-v1",
        "repository_identity": repository["repository_identity"],
        "branch": repository["branch"],
        "head_sha": repository["head_sha"],
        "latest_commit_timestamp": repository["latest_commit_timestamp"],
        "working_tree_status": repository["working_tree_status"],
        "active_mission": mission["active_mission"],
        "mission_stage": mission["mission_stage"],
        "project_progress": _unknown_claim("No authoritative project-wide gate definition exists.", "executive_state", generated_at),
        "current_sprint": sprint,
        "sprint_progress": _unknown_claim("No durable sprint progress record exists.", "sprint_engine", generated_at),
        "release_stage": release,
        "open_prs": github["open_prs"],
        "ci_check_status": github["ci_check_status"],
        "latest_merge": github["latest_merge"],
        "deployed_revision": deployment["deployed_revision"],
        "deployment_traffic": deployment["deployment_traffic"],
        "production_verification": verification,
        "platform_health": health,
        "blockers": blockers,
        "risks": risks,
        "next_recommended_action": next_action,
        "source_evidence": sources,
        "governance": {
            "read_only": True,
            "repository_mutation": False,
            "github_mutation": False,
            "approval_mutation": False,
            "deployment": False,
            "traffic_shift": False,
            "secrets_exposed": False,
            "founder_approval_boundaries_preserved": True,
        },
    }


def _collect(name: str, collector: Callable[[], Any], checked_at: str) -> Dict[str, Any]:
    try:
        value = collector()
    except Exception as exc:
        return {
            "status": UNKNOWN,
            "value": None,
            "source": name,
            "evidence_type": "source_error",
            "checked_at": checked_at,
            "freshness": "checked-on-request",
            "confidence": "none",
            "unknown_reason": "%s failed: %s" % (name, type(exc).__name__),
        }
    return {
        "status": "observed",
        "value": value,
        "source": name,
        "evidence_type": "live_read",
        "checked_at": checked_at,
        "freshness": "checked-on-request",
        "confidence": "high",
        "unknown_reason": None,
    }


def _claim(value: Any, source: str, evidence_type: str, checked_at: str, confidence: str = "high") -> Dict[str, Any]:
    return {
        "status": "observed" if value is not None else UNKNOWN,
        "value": value,
        "source": source,
        "evidence_type": evidence_type,
        "checked_at": checked_at,
        "freshness": "checked-on-request",
        "confidence": confidence if value is not None else "none",
        "unknown_reason": None if value is not None else "The source did not provide this evidence.",
    }


def _unknown_claim(reason: str, source: str, checked_at: str) -> Dict[str, Any]:
    value = _claim(None, source, "unavailable_evidence", checked_at, "none")
    value["unknown_reason"] = reason
    return value


def _source_value(source: Dict[str, Any]) -> Dict[str, Any]:
    value = source.get("value")
    return value if source.get("status") == "observed" and isinstance(value, dict) else {}


def _claim_from_source(source: Dict[str, Any], name: str, checked_at: str) -> Dict[str, Any]:
    value = _source_value(source)
    if not value or value.get("status") == UNKNOWN:
        reason = source.get("unknown_reason") or value.get("unknown_reason") or "No authoritative %s evidence exists." % name.replace("_", " ")
        return _unknown_claim(str(reason), str(source.get("source") or name), checked_at)
    return _claim(value, str(source.get("source") or name), "operational_record", checked_at)


def _repository_state() -> Dict[str, Any]:
    def run(*args: str) -> str:
        result = subprocess.run(
            ["git"] + list(args), cwd=str(REPO_ROOT), text=True, capture_output=True,
            check=False, timeout=5,
        )
        if result.returncode != 0:
            raise RuntimeError("Git repository evidence is unavailable.")
        return result.stdout.strip()

    return {
        "repository": PRIMARY_REPOSITORY,
        "branch": run("branch", "--show-current") or None,
        "head_sha": run("rev-parse", "HEAD"),
        "latest_commit_timestamp": run("log", "-1", "--format=%cI"),
        "working_tree_status": run("status", "--porcelain"),
    }


def _repository_claims(source: Dict[str, Any], checked_at: str) -> Dict[str, Dict[str, Any]]:
    value = _source_value(source)
    reason = str(source.get("unknown_reason") or "Repository checkout metadata is unavailable.")
    fields = ("repository", "branch", "head_sha", "latest_commit_timestamp", "working_tree_status")
    claims = {
        field: _claim(value.get(field), "git_repository", "git_command", checked_at)
        if value and (field in value)
        else _unknown_claim(reason, "git_repository", checked_at)
        for field in fields
    }
    claims["repository_identity"] = claims.pop("repository")
    return claims


def _mission_claims(source: Dict[str, Any], checked_at: str) -> Dict[str, Dict[str, Any]]:
    pipeline = _source_value(source)
    missions = pipeline.get("active_missions") if isinstance(pipeline.get("active_missions"), list) else []
    if not missions:
        reason = source.get("unknown_reason") or "No active durable mission was observed."
        return {
            "active_mission": _unknown_claim(str(reason), "mission_pipeline", checked_at),
            "mission_stage": _unknown_claim(str(reason), "mission_pipeline", checked_at),
        }
    mission = missions[0]
    stage = mission.get("current_stage") or mission.get("current_autonomous_stage") or mission.get("status")
    return {
        "active_mission": _claim(mission, "mission_pipeline", "durable_workflow_projection", checked_at),
        "mission_stage": _claim(stage, "mission_pipeline", "derived_from_durable_mission", checked_at),
    }


def _github_state() -> Dict[str, Any]:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {"status": UNKNOWN, "unknown_reason": "GITHUB_TOKEN is not mounted; live PR evidence is unavailable."}
    from app.platform.github_execution.pr_lifecycle import _github_get, _normalize_checks, _summarize_checks

    open_prs = _github_get("/pulls", token, params={"state": "open", "per_page": 20})
    closed_prs = _github_get("/pulls", token, params={"state": "closed", "sort": "updated", "direction": "desc", "per_page": 20})
    latest_merge = next((item for item in closed_prs if item.get("merged_at")), None)
    checks = []
    if open_prs:
        sha = str(((open_prs[0].get("head") or {}).get("sha")) or "")
        if sha:
            checks = _normalize_checks(_github_get("/commits/%s/check-runs" % sha, token, params={"per_page": 100}))
    return {
        "status": "observed",
        "open_prs": [{"number": item.get("number"), "title": item.get("title"), "url": item.get("html_url"), "head_sha": (item.get("head") or {}).get("sha")} for item in open_prs],
        "checks": checks,
        "checks_summary": _summarize_checks(checks) if checks else None,
        "checks_unknown_reason": "No open pull request with a head commit was available for check inspection.",
        "latest_merge": {"number": latest_merge.get("number"), "title": latest_merge.get("title"), "merged_at": latest_merge.get("merged_at"), "merge_commit_sha": latest_merge.get("merge_commit_sha")} if latest_merge else None,
    }


def _github_claims(source: Dict[str, Any], checked_at: str) -> Dict[str, Dict[str, Any]]:
    value = _source_value(source)
    if not value or value.get("status") == UNKNOWN:
        reason = source.get("unknown_reason") or value.get("unknown_reason") or "Live GitHub evidence is unavailable."
        return {key: _unknown_claim(str(reason), "github_api", checked_at) for key in ("open_prs", "ci_check_status", "latest_merge")}
    return {
        "open_prs": _claim(value.get("open_prs", []), "github_api", "live_api_read", checked_at),
        "ci_check_status": _claim(value.get("checks_summary"), "github_api", "live_check_runs", checked_at)
        if value.get("checks_summary") is not None
        else _unknown_claim(str(value.get("checks_unknown_reason") or "No current CI check evidence exists."), "github_api", checked_at),
        "latest_merge": _claim(value.get("latest_merge"), "github_api", "live_pull_request_read", checked_at) if value.get("latest_merge") else _unknown_claim("No merged pull request was returned by the bounded GitHub query.", "github_api", checked_at),
    }


def _deployment_state() -> Dict[str, Any]:
    revision = os.getenv("K_REVISION")
    service = os.getenv("K_SERVICE")
    if not revision:
        return {"status": UNKNOWN, "unknown_reason": "K_REVISION is unavailable outside a deployed Cloud Run revision."}
    return {"status": "observed", "revision": revision, "service": service, "traffic": None}


def _deployment_claims(source: Dict[str, Any], checked_at: str) -> Dict[str, Dict[str, Any]]:
    value = _source_value(source)
    if not value or value.get("status") == UNKNOWN:
        reason = source.get("unknown_reason") or value.get("unknown_reason") or "Deployment evidence is unavailable."
        return {
            "deployed_revision": _unknown_claim(str(reason), "cloud_run_runtime", checked_at),
            "deployment_traffic": _unknown_claim(str(reason), "cloud_run_runtime", checked_at),
        }
    return {
        "deployed_revision": _claim(value.get("revision"), "cloud_run_runtime", "runtime_environment", checked_at),
        "deployment_traffic": _claim(value.get("traffic"), "cloud_run_runtime", "runtime_environment", checked_at) if value.get("traffic") is not None else _unknown_claim("Cloud Run traffic allocation is not available in the runtime environment.", "cloud_run_runtime", checked_at),
    }


def _verification_state() -> Dict[str, Any]:
    return {"status": UNKNOWN, "unknown_reason": "Production verification results are not stored as an authoritative durable record."}


def _sprint_state() -> Dict[str, Any]:
    return {"status": UNKNOWN, "unknown_reason": "Sprint Engine creates plans but has no authoritative durable current-sprint record."}


def _release_state() -> Dict[str, Any]:
    return {"status": UNKNOWN, "unknown_reason": "Release Flow contains demo records and is not authoritative production release evidence."}


def _health_claim(source: Dict[str, Any], checked_at: str) -> Dict[str, Any]:
    value = _source_value(source)
    if not value:
        return _unknown_claim(str(source.get("unknown_reason") or "Platform health is unavailable."), "platform_health", checked_at)
    return _claim(value, "platform_health", "process_health_read", checked_at, "medium")


def _derive_blockers(sources: Dict[str, Dict[str, Any]], mission: Dict[str, Dict[str, Any]], github: Dict[str, Dict[str, Any]], deployment: Dict[str, Dict[str, Any]], verification: Dict[str, Any], health: Dict[str, Any], checked_at: str) -> Dict[str, Any]:
    items: List[Dict[str, str]] = []
    active = mission["active_mission"].get("value") or {}
    if isinstance(active, dict) and active.get("blocker"):
        items.append({"source": "mission_pipeline", "reason": str(active["blocker"])})
    checks = github["ci_check_status"].get("value") or {}
    if isinstance(checks, dict) and checks.get("overall") in {"failing", "failure"}:
        items.append({"source": "github_api", "reason": "Current pull-request checks are failing."})
    if health.get("value") and health["value"].get("status") not in {"healthy", "ready"}:
        items.append({"source": "platform_health", "reason": "Platform health is not healthy."})
    unavailable = [name for name in ("missions", "github", "health") if sources[name].get("status") == UNKNOWN]
    if not items and unavailable:
        return _unknown_claim(
            "Blockers cannot be determined because these current sources are unavailable: %s." % ", ".join(unavailable),
            "executive_state",
            checked_at,
        )
    return _claim(items, "executive_state", "derived_conclusion", checked_at, "high" if items else "medium")


def _derive_risks(sources: Dict[str, Dict[str, Any]], repository: Dict[str, Dict[str, Any]], github: Dict[str, Dict[str, Any]], deployment: Dict[str, Dict[str, Any]], checked_at: str) -> Dict[str, Any]:
    risks: List[Dict[str, str]] = []
    if repository["working_tree_status"].get("value"):
        risks.append({"source": "git_repository", "reason": "The observed repository working tree contains uncommitted changes."})
    for name in ("github", "deployment"):
        if sources[name].get("status") == UNKNOWN:
            risks.append({"source": name, "reason": str(sources[name].get("unknown_reason"))})
    return _claim(risks, "executive_state", "derived_conclusion", checked_at, "medium")


def _derive_next_action(mission: Dict[str, Dict[str, Any]], github: Dict[str, Dict[str, Any]], deployment: Dict[str, Dict[str, Any]], verification: Dict[str, Any], blockers: Dict[str, Any], checked_at: str) -> Dict[str, Any]:
    if blockers.get("value"):
        return _claim("Resolve the first current evidence-backed blocker.", "executive_state", "derived_conclusion", checked_at, "high")
    active = mission["active_mission"].get("value") or {}
    if isinstance(active, dict):
        action = active.get("next_recommended_action") or (active.get("recommendation") or {}).get("action")
        if action:
            return _claim(action, "mission_pipeline", "derived_from_durable_mission", checked_at, "high")
    if github["open_prs"].get("value"):
        return _claim("Review the current pull request and CI checks.", "github_api", "derived_conclusion", checked_at, "high")
    return _unknown_claim("No authoritative active mission or actionable operational transition was observed.", "executive_state", checked_at)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
