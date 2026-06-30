from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from app.platform.runtime.service import invoke_ai


ENGINEERING_ROLES = ["architect", "backend", "qa", "devops", "scribe"]


def build_autonomous_engineering_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Autonomous Engineering Worker",
        "milestone": "GCP-08",
        "status": "autonomous-engineering-worker-ready",
        "mode": "planning-only",
        "governance_rule": "The worker prepares implementation blueprints only. Code changes and pull requests still require explicit founder-approved execution in later milestones.",
        "endpoints": {
            "summary": "GET /mission-control/engineering-worker",
            "blueprint": "POST /mission-control/engineering-worker/blueprint",
            "pr_plan": "POST /mission-control/engineering-worker/pr-plan",
        },
        "worker_roles": ENGINEERING_ROLES,
        "next_step": "GCP-09 Repository Intelligence and File Context Loader",
    }


def create_engineering_blueprint(payload: dict[str, Any]) -> dict[str, Any]:
    created_at = _now()
    mission = _normalize_mission(payload)
    blueprint_id = _id("BLUEPRINT", created_at, mission)
    deterministic = _deterministic_blueprint(blueprint_id=blueprint_id, created_at=created_at, mission=mission)
    ai_prompt = _blueprint_prompt(mission=mission, deterministic=deterministic)
    ai_result = invoke_ai(
        {
            "system": "You are the senior autonomous engineering planner inside AI Software Factory. Return concise implementation guidance only. Do not claim code has been changed.",
            "prompt": ai_prompt,
            "model": payload.get("model") or os.getenv("OPENAI_MODEL", "gpt-5.5"),
        }
    )
    return {
        "company": "AI Software Factory",
        "product": "Autonomous Engineering Worker",
        "milestone": "GCP-08",
        "status": "blueprint-created" if ai_result.get("status") == "completed" else f"blueprint-{ai_result.get('status', 'unknown')}",
        "blueprint_id": blueprint_id,
        "mission_id": mission["mission_id"],
        "mode": "planning-only",
        "blueprint": deterministic,
        "ai_guidance": ai_result,
        "next_step": "Founder review, then GCP-09 repository context loading.",
    }


def create_pr_plan(payload: dict[str, Any]) -> dict[str, Any]:
    created_at = _now()
    mission = _normalize_mission(payload)
    plan_id = _id("PRPLAN", created_at, mission)
    blueprint = payload.get("blueprint") if isinstance(payload.get("blueprint"), dict) else {}
    pr_plan = {
        "pr_plan_id": plan_id,
        "mission_id": mission["mission_id"],
        "created_at": created_at,
        "branch_name": _safe_branch_name(mission["mission_id"], mission["title"]),
        "title": f"Implement {mission['title']}",
        "summary": mission["goal"],
        "proposed_files": blueprint.get("proposed_files") or _default_files(mission),
        "validation_gates": [
            "python -m compileall app",
            "python -m app.platform.api_contract",
            "bash infra/scripts/gate.sh",
            "Manual production endpoint verification after Platform Deploy",
        ],
        "founder_approval_required": True,
        "execution_mode": "future-autonomous-pr-generation",
    }
    ai_result = invoke_ai(
        {
            "system": "You are the pull request planner for AI Software Factory. Return concise PR guidance only.",
            "prompt": "Create a pull request plan for this mission and blueprint.\n\n" + json.dumps({"mission": mission, "pr_plan": pr_plan, "blueprint": blueprint}, sort_keys=True),
            "model": payload.get("model") or os.getenv("OPENAI_MODEL", "gpt-5.5"),
        }
    )
    return {
        "company": "AI Software Factory",
        "product": "Autonomous Engineering Worker",
        "milestone": "GCP-08",
        "status": "pr-plan-created" if ai_result.get("status") == "completed" else f"pr-plan-{ai_result.get('status', 'unknown')}",
        "pr_plan_id": plan_id,
        "mission_id": mission["mission_id"],
        "pr_plan": pr_plan,
        "ai_guidance": ai_result,
        "next_step": "GCP-09 Repository Intelligence and GCP-10 Autonomous Code Generation.",
    }


def _deterministic_blueprint(*, blueprint_id: str, created_at: str, mission: dict[str, Any]) -> dict[str, Any]:
    return {
        "blueprint_id": blueprint_id,
        "mission_id": mission["mission_id"],
        "created_at": created_at,
        "status": "draft-for-founder-review",
        "objective": mission["goal"],
        "implementation_strategy": [
            "Clarify scope and acceptance criteria.",
            "Identify API surface, service modules, and repository artifacts.",
            "Create minimal safe implementation behind existing validation gates.",
            "Open a founder-visible pull request for review before merge.",
        ],
        "work_packages": [
            {"role": "architect", "task": "Confirm architecture impact and boundaries."},
            {"role": "backend", "task": "Implement service and API changes."},
            {"role": "qa", "task": "Update API contract and validation checklist."},
            {"role": "devops", "task": "Confirm deploy and rollback path."},
            {"role": "scribe", "task": "Record release notes and audit trail."},
        ],
        "proposed_files": _default_files(mission),
        "risks": [
            "AI-generated plans may omit repository-specific constraints until repository intelligence is added.",
            "Code generation is intentionally deferred until founder approval and repository context are available.",
        ],
        "acceptance_criteria": mission["acceptance_criteria"] or ["Blueprint and PR plan are created for founder review."],
        "rollback_plan": "Do not execute code changes. Discard blueprint or regenerate after founder feedback.",
    }


def _blueprint_prompt(*, mission: dict[str, Any], deterministic: dict[str, Any]) -> str:
    return (
        "Create an autonomous engineering blueprint for this approved mission.\n"
        "Do not modify code. Do not claim a PR exists.\n"
        "Return concise structured text with: architecture, files, implementation tasks, tests, risks, approval handoff.\n\n"
        + json.dumps({"mission": mission, "baseline_blueprint": deterministic}, sort_keys=True)
    )


def _normalize_mission(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("mission") if isinstance(payload.get("mission"), dict) else payload
    acceptance = source.get("acceptance_criteria") or source.get("acceptanceCriteria") or []
    if isinstance(acceptance, str):
        acceptance = [line.strip() for line in acceptance.splitlines() if line.strip()]
    if not isinstance(acceptance, list):
        acceptance = [str(acceptance)]
    return {
        "mission_id": str(source.get("mission_id") or source.get("id") or "MISSION-UNSPECIFIED").strip(),
        "proposal_id": str(source.get("proposal_id") or "PROP-UNSPECIFIED").strip(),
        "request_id": str(source.get("request_id") or "REQ-UNSPECIFIED").strip(),
        "title": str(source.get("mission_title") or source.get("title") or "Approved engineering mission").strip(),
        "goal": str(source.get("goal") or source.get("description") or "Prepare an implementation plan for the approved mission.").strip(),
        "current_context": str(source.get("current_context") or source.get("context") or "").strip(),
        "acceptance_criteria": [str(item).strip() for item in acceptance if str(item).strip()],
    }


def _default_files(mission: dict[str, Any]) -> list[str]:
    title = f"{mission['title']} {mission['goal']}".lower()
    files = ["app/platform/server.py", "app/platform/api_contract.py"]
    if "auth" in title or "login" in title:
        files.insert(0, "app/platform/auth/service.py")
    elif "runtime" in title or "worker" in title:
        files.insert(0, "app/platform/runtime/service.py")
    else:
        files.insert(0, "app/platform/autonomous_engineering/service.py")
    return files


def _safe_branch_name(mission_id: str, title: str) -> str:
    raw = f"mission/{mission_id}-{title}".lower()
    cleaned = "".join(char if char.isalnum() else "-" for char in raw)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")[:80]


def _id(prefix: str, timestamp: str, data: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}-{timestamp[:10].replace('-', '')}-{digest}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
