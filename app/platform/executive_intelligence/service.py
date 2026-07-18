from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.platform.capability_intelligence.service import get_capability_intelligence_status
from app.platform.health.health_status import build_health_status
from app.platform.pipeline.mission_pipeline import build_mission_pipeline_summary
from app.platform.executive_intelligence.evidence_registry import collect_evidence
from app.platform.executive_intelligence.board_room_integration import inspect_board_room_integration
from app.platform.executive_intelligence.operational_authority import (
    project_gates,
    release_authority,
    sprint_authority,
    verification_authority,
)

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
        "verification": verification_authority,
        "health": build_health_status,
        "sprint": sprint_authority,
        "release": release_authority,
        "board_room": inspect_board_room_integration,
    }
    collectors.update(source_overrides or {})
    sources = {
        name: collect_evidence(name, collector, generated_at)
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
    gates = project_gates(mission, github, _source_value(sources["release"]), _source_value(sources["verification"]))
    blockers = _derive_blockers(sources, mission, github, deployment, verification, health, generated_at)
    risks = _derive_risks(sources, repository, github, deployment, generated_at)
    next_action = _derive_next_action(mission, github, deployment, verification, blockers, generated_at)
    return {
        "company": "AI Software Factory",
        "product": "Executive Intelligence Layer",
        "milestone": "SPRINT-3-P0-EXECUTIVE-BRAIN-EVIDENCE",
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
        "project_progress": _claim(gates, "project_gates", "derived_from_canonical_gates", generated_at),
        "project_gates": gates["gates"],
        "current_sprint": sprint,
        "sprint_progress": _claim((sprint.get("value") or {}).get("progress"), "platform_workflow_runs", "derived_from_durable_sprint", generated_at) if sprint.get("value") else _unknown_claim("No durable sprint progress evidence exists.", "platform_workflow_runs", generated_at),
        "release_stage": release,
        "open_prs": github["open_prs"],
        "github_branch": github["github_branch"],
        "github_head_sha": github["github_head_sha"],
        "ci_check_status": github["ci_check_status"],
        "latest_merge": github["latest_merge"],
        "workflow_status": github["workflow_status"],
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

    try:
        return {
            "repository": PRIMARY_REPOSITORY,
            "branch": run("branch", "--show-current") or None,
            "head_sha": run("rev-parse", "HEAD"),
            "latest_commit_timestamp": run("log", "-1", "--format=%cI"),
            "working_tree_status": run("status", "--porcelain"),
        }
    except (RuntimeError, OSError):
        sha = os.getenv("SOURCE_COMMIT_SHA")
        branch = os.getenv("SOURCE_BRANCH")
        if not sha or not branch:
            raise
        return {
            "repository": PRIMARY_REPOSITORY,
            "branch": branch,
            "head_sha": sha,
            "latest_commit_timestamp": os.getenv("SOURCE_COMMIT_TIMESTAMP"),
            "working_tree_status": "not-applicable-immutable-deployment",
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
    from app.platform.github_execution.pr_lifecycle import _github_get, _normalize_checks, _summarize_checks

    errors: Dict[str, str] = {}

    def read(name: str, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        try:
            return _github_get(path, token or "", params=params)
        except RuntimeError:
            errors[name] = "GitHub %s evidence is unavailable to the configured read credential." % name.replace("_", " ")
            return None

    open_prs = read("open_prs", "/pulls", {"state": "open", "per_page": 20})
    closed_prs = read("latest_merge", "/pulls", {"state": "closed", "sort": "updated", "direction": "desc", "per_page": 20})
    repository = read("repository", "") or {}
    default_branch = str(repository.get("default_branch") or os.getenv("SOURCE_BRANCH") or "main")
    branch = read("branch", "/branches/%s" % default_branch) or {}
    workflows = read("workflow_status", "/actions/runs", {"branch": default_branch, "per_page": 10})
    latest_merge = next((item for item in (closed_prs or []) if item.get("merged_at")), None)
    checks = []
    if open_prs:
        sha = str(((open_prs[0].get("head") or {}).get("sha")) or "")
        if sha:
            checks_payload = read("checks", "/commits/%s/check-runs" % sha, {"per_page": 100})
            if checks_payload:
                checks = _normalize_checks(checks_payload)
    workflow_runs = (workflows or {}).get("workflow_runs") or []
    if not checks and workflow_runs:
        latest_workflow = workflow_runs[0]
        conclusion = latest_workflow.get("conclusion")
        status = latest_workflow.get("status")
        checks = [{
            "name": latest_workflow.get("name"),
            "type": "workflow_run",
            "status": status,
            "conclusion": conclusion,
            "url": latest_workflow.get("html_url"),
        }]
    return {
        "status": "partial" if errors else "observed",
        "open_prs": None if open_prs is None else [{"number": item.get("number"), "title": item.get("title"), "url": item.get("html_url"), "head_sha": (item.get("head") or {}).get("sha")} for item in open_prs],
        "checks": checks,
        "checks_summary": _summarize_checks(checks) if checks else None,
        "checks_unknown_reason": errors.get("checks") or errors.get("workflow_status") or "No pull-request checks or default-branch workflow runs were available.",
        "latest_merge": {"number": latest_merge.get("number"), "title": latest_merge.get("title"), "merged_at": latest_merge.get("merged_at"), "merge_commit_sha": latest_merge.get("merge_commit_sha")} if latest_merge else None,
        "branch": default_branch,
        "head_sha": ((branch.get("commit") or {}).get("sha")) or os.getenv("SOURCE_COMMIT_SHA"),
        "workflow_status": None if workflows is None else [{"name": item.get("name"), "status": item.get("status"), "conclusion": item.get("conclusion"), "head_sha": item.get("head_sha"), "updated_at": item.get("updated_at"), "url": item.get("html_url")} for item in workflow_runs],
        "errors": errors,
        "evidence_errors": errors,
    }


def _github_claims(source: Dict[str, Any], checked_at: str) -> Dict[str, Dict[str, Any]]:
    value = _source_value(source)
    if not value or value.get("status") == UNKNOWN:
        reason = source.get("unknown_reason") or value.get("unknown_reason") or "Live GitHub evidence is unavailable."
        return {key: _unknown_claim(str(reason), "github_api", checked_at) for key in ("open_prs", "github_branch", "github_head_sha", "ci_check_status", "latest_merge", "workflow_status")}
    return {
        "open_prs": _github_field_claim(value, "open_prs", "open_prs", checked_at, "live_api_read"),
        "github_branch": _github_field_claim(value, "branch", "repository", checked_at, "live_repository_read"),
        "github_head_sha": _github_field_claim(value, "head_sha", "branch", checked_at, "live_repository_read"),
        "ci_check_status": _claim(value.get("checks_summary"), "github_api", "live_check_runs", checked_at)
        if value.get("checks_summary") is not None
        else _unknown_claim(str(value.get("checks_unknown_reason") or "No current CI check evidence exists."), "github_api", checked_at),
        "latest_merge": _github_field_claim(value, "latest_merge", "latest_merge", checked_at, "live_pull_request_read", "No merged pull request was returned by the bounded GitHub query."),
        "workflow_status": _github_field_claim(value, "workflow_status", "workflow_status", checked_at, "live_actions_read"),
    }


def _github_field_claim(value: Dict[str, Any], field: str, error_key: str, checked_at: str, evidence_type: str, empty_reason: Optional[str] = None) -> Dict[str, Any]:
    errors = value.get("errors") if isinstance(value.get("errors"), dict) else {}
    if error_key in errors and value.get(field) is None:
        return _unknown_claim(str(errors[error_key]), "github_api", checked_at)
    if value.get(field) is None and empty_reason:
        return _unknown_claim(empty_reason, "github_api", checked_at)
    return _claim(value.get(field), "github_api", evidence_type, checked_at)


def _deployment_state() -> Dict[str, Any]:
    release = release_authority()
    if release.get("status") == UNKNOWN:
        return release
    return {
        "status": "observed",
        "revision": release.get("active_revision") or release.get("revision"),
        "service": release.get("service"),
        "traffic": release.get("traffic"),
        "deployment_history": release.get("deployment_history") or [],
    }


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
