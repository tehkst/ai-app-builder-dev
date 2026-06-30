from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.platform.founder_workspace.github_adapter import (
    GitHubRequestWriteAdapter,
    GitHubRequestWriteConfig,
    GitHubRequestWriteError,
)

AGENTS = ["architect", "backend", "qa", "devops", "scribe"]


def build_mission_execution_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Mission Execution Bridge",
        "milestone": "GCP-05",
        "status": "mission-execution-bridge-ready",
        "governance_rule": "Only approved missions may be planned for execution.",
        "endpoints": {
            "summary": "GET /mission-control/missions",
            "mission_status": "GET /mission-control/missions/{mission_id}",
            "plan": "POST /mission-control/missions/plan",
            "start": "POST /mission-control/missions/start",
        },
        "execution_states": ["created", "planned", "ready-for-execution", "in-progress", "blocked", "completed"],
        "agent_roles": AGENTS,
        "next_step": "Agent Orchestration Runtime",
    }


def get_mission_status(mission_id: str) -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Mission Execution Bridge",
        "mission_id": mission_id,
        "status": "created",
        "execution_state": "awaiting-plan",
        "allowed_actions": ["plan"],
        "next_step": "POST /mission-control/missions/plan",
    }


def plan_mission(payload: dict[str, Any]) -> dict[str, Any]:
    planned_at = _now()
    mission = _normalize_mission(payload)
    plan_id = _id("PLAN", planned_at, {"mission_id": mission["mission_id"]})
    plan = {
        "plan_id": plan_id,
        "mission_id": mission["mission_id"],
        "proposal_id": mission["proposal_id"],
        "request_id": mission["request_id"],
        "approval_id": mission["approval_id"],
        "status": "planned",
        "planned_at": planned_at,
        "execution_state": "ready-for-execution",
        "work_packages": _work_packages(plan_id),
        "acceptance_criteria": mission["acceptance_criteria"] or ["Mission plan is ready for execution."],
        "gates": ["CI-01 PR Validation", "Founder-visible PR", "Manual Platform Deploy", "Production verification"],
    }
    artifact_path = _artifact_path("execution-plans", planned_at, plan_id, "json")
    write_result = _write_artifact(plan_id, artifact_path, json.dumps(plan, indent=2, sort_keys=True) + "\n", f"Plan mission {mission['mission_id']}")
    status = "planned" if write_result["mode"] == "github" else f"planned-{write_result['mode']}"
    return {
        "company": "AI Software Factory",
        "product": "Mission Execution Bridge",
        "status": status,
        "mission_id": mission["mission_id"],
        "plan_id": plan_id,
        "execution_state": "ready-for-execution",
        "plan_artifact_path": artifact_path,
        "execution_plan": plan,
        "repository_write": write_result,
        "next_step": "POST /mission-control/missions/start",
    }


def start_mission(payload: dict[str, Any]) -> dict[str, Any]:
    started_at = _now()
    mission_id = _text(payload, "mission_id", "MISSION-UNSPECIFIED")
    plan_id = _text(payload, "plan_id", "PLAN-UNSPECIFIED")
    started_by = _text(payload, "started_by", _text(payload, "actor", "Founder"))
    run_id = _id("RUN", started_at, {"mission_id": mission_id, "plan_id": plan_id, "started_by": started_by})
    run = {
        "run_id": run_id,
        "mission_id": mission_id,
        "plan_id": plan_id,
        "status": "in-progress",
        "started_at": started_at,
        "started_by": started_by,
        "agent_dispatch": [{"role": role, "status": "queued"} for role in AGENTS],
        "governance": "Execution is traceable to founder approval.",
    }
    artifact_path = _artifact_path("mission-runs", started_at, run_id, "json")
    write_result = _write_artifact(run_id, artifact_path, json.dumps(run, indent=2, sort_keys=True) + "\n", f"Start mission {mission_id}")
    status = "in-progress" if write_result["mode"] == "github" else f"in-progress-{write_result['mode']}"
    return {
        "company": "AI Software Factory",
        "product": "Mission Execution Bridge",
        "status": status,
        "mission_id": mission_id,
        "plan_id": plan_id,
        "run_id": run_id,
        "run_artifact_path": artifact_path,
        "run": run,
        "repository_write": write_result,
        "next_step": "Agent Orchestration Runtime",
    }


def _work_packages(plan_id: str) -> list[dict[str, str]]:
    return [
        {"id": f"{plan_id}-WP1", "agent_role": "architect", "title": "Confirm architecture boundaries"},
        {"id": f"{plan_id}-WP2", "agent_role": "backend", "title": "Implement approved changes"},
        {"id": f"{plan_id}-WP3", "agent_role": "qa", "title": "Validate acceptance criteria"},
        {"id": f"{plan_id}-WP4", "agent_role": "devops", "title": "Prepare deployment and rollback"},
        {"id": f"{plan_id}-WP5", "agent_role": "scribe", "title": "Record audit trail"},
    ]


def _normalize_mission(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("mission") if isinstance(payload.get("mission"), dict) else payload
    return {
        "mission_id": _text(source, "mission_id", _text(source, "id", "MISSION-UNSPECIFIED")),
        "proposal_id": _text(source, "proposal_id", "PROP-UNSPECIFIED"),
        "request_id": _text(source, "request_id", "REQ-UNSPECIFIED"),
        "approval_id": _text(source, "approval_id", "APPR-UNSPECIFIED"),
        "acceptance_criteria": _list(source.get("acceptance_criteria") or source.get("acceptanceCriteria")),
    }


def _write_artifact(artifact_id: str, path: str, content: str, title: str) -> dict[str, Any]:
    config = GitHubRequestWriteConfig.from_environment()
    if config is None:
        return {"mode": "pending-github-configuration"}
    try:
        result = GitHubRequestWriteAdapter(config).write_request_artifact(
            request_id=artifact_id,
            artifact_path=path,
            content=content,
            title=title,
        )
    except GitHubRequestWriteError as exc:
        return {"mode": "github-write-failed", "error": str(exc)}
    return {"mode": result.mode, "repository": result.repository, "branch": result.branch, "path": result.path, "commit_sha": result.commit_sha}


def _artifact_path(kind: str, timestamp: str, artifact_id: str, extension: str) -> str:
    year, month, _day = timestamp[:10].split("-")
    return f"company/{kind}/{year}/{month}/{artifact_id}.{extension}"


def _id(prefix: str, timestamp: str, data: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}-{timestamp[:10].replace('-', '')}-{digest}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _text(payload: dict[str, Any], key: str, default: str) -> str:
    value = str(payload.get(key) or default).strip()
    return value or default


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]
