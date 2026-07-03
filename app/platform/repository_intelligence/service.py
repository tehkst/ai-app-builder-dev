from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.platform.constitution.runtime import build_constitution_context
from app.platform.runtime.service import invoke_ai


CORE_REPOSITORY_AREAS = {
    "api": ["app/platform/server.py", "app/platform/api_contract.py"],
    "runtime": ["app/platform/runtime/service.py", "app/platform/runtime/ai_provider.py"],
    "engineering_worker": ["app/platform/autonomous_engineering/service.py"],
    "mission_execution": ["app/platform/mission_execution/service.py"],
    "founder_approval": ["app/platform/founder_approval/service.py"],
    "proposal_generator": ["app/platform/proposal_generator/service.py"],
    "founder_workspace": ["app/platform/founder_workspace/service.py"],
    "ci": [".github/workflows/pr-validation.yml", "infra/scripts/gate.sh"],
    "deploy": [".github/workflows/platform-deploy.yml", "Dockerfile"],
    "constitution": ["app/platform/constitution/runtime.py", "app/platform/constitution/service.py", "app/platform/constitution/binder.py"],
}


def build_repository_intelligence_summary() -> dict[str, Any]:
    constitution = build_constitution_context()
    return {
        "company": "AI Software Factory",
        "product": "Repository Intelligence",
        "milestone": "GCP-09",
        "status": "repository-intelligence-ready",
        "mode": "static-map-plus-ai-guidance",
        "purpose": "Select repository context and file plans before autonomous code generation.",
        "runtime_constitution": constitution,
        "endpoints": {
            "summary": "GET /mission-control/repository",
            "index": "POST /mission-control/repository/index",
            "context": "POST /mission-control/repository/context",
            "search": "POST /mission-control/repository/search",
            "file_plan": "POST /mission-control/repository/file-plan",
        },
        "repository_areas": CORE_REPOSITORY_AREAS,
        "next_step": "GCP-10 Autonomous Code Generation",
    }


def build_repository_index(payload: dict[str, Any]) -> dict[str, Any]:
    indexed_at = _now()
    repo = str(payload.get("repository") or "tehkst/ai-app-builder-dev").strip()
    index_id = _id("REPOINDEX", indexed_at, {"repository": repo})
    return {
        "company": "AI Software Factory",
        "product": "Repository Intelligence",
        "milestone": "GCP-09",
        "status": "indexed",
        "repository": repo,
        "index_id": index_id,
        "indexed_at": indexed_at,
        "runtime_constitution": build_constitution_context(),
        "areas": [
            {"area": area, "files": files, "purpose": _area_purpose(area)}
            for area, files in CORE_REPOSITORY_AREAS.items()
        ],
        "limitations": [
            "GCP-09 uses a curated repository map. Full tree scanning and embeddings are deferred.",
            "File contents are not loaded directly by this endpoint.",
        ],
        "next_step": "POST /mission-control/repository/context",
    }


def build_repository_context(payload: dict[str, Any]) -> dict[str, Any]:
    mission = _normalize_mission(payload)
    selected = _select_files(mission)
    context_id = _id("CTX", _now(), {"mission": mission, "files": selected})
    constitution = build_constitution_context()
    ai_result = invoke_ai(
        {
            "system": "You are repository intelligence for AI Software Factory. Recommend only relevant files and explain why while following the runtime Constitution.",
            "prompt": "Create a concise repository context pack for this mission.\n" + json.dumps({"mission": mission, "selected_files": selected, "repository_areas": CORE_REPOSITORY_AREAS, "runtime_constitution": constitution}, sort_keys=True),
            "model": payload.get("model"),
        }
    )
    return {
        "company": "AI Software Factory",
        "product": "Repository Intelligence",
        "milestone": "GCP-09",
        "status": "context-created" if ai_result.get("status") == "completed" else f"context-{ai_result.get('status', 'unknown')}",
        "context_id": context_id,
        "mission_id": mission["mission_id"],
        "runtime_constitution": constitution,
        "selected_files": selected,
        "context_pack": [
            {"path": path, "reason": _file_reason(path, mission)} for path in selected
        ],
        "ai_guidance": ai_result,
        "next_step": "POST /mission-control/repository/file-plan",
    }


def search_repository(payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query") or payload.get("q") or "").lower().strip()
    matches: list[dict[str, str]] = []
    for area, files in CORE_REPOSITORY_AREAS.items():
        haystack = f"{area} {' '.join(files)}".lower()
        if not query or query in haystack or any(token in haystack for token in query.split()):
            for path in files:
                matches.append({"area": area, "path": path, "reason": _area_purpose(area)})
    return {
        "company": "AI Software Factory",
        "product": "Repository Intelligence",
        "milestone": "GCP-09",
        "status": "search-complete",
        "query": query,
        "runtime_constitution": build_constitution_context(),
        "matches": matches[:20],
        "next_step": "Use matches to build a context pack or file plan.",
    }


def build_file_plan(payload: dict[str, Any]) -> dict[str, Any]:
    mission = _normalize_mission(payload)
    files = payload.get("selected_files") if isinstance(payload.get("selected_files"), list) else _select_files(mission)
    plan_id = _id("FILEPLAN", _now(), {"mission": mission, "files": files})
    constitution = build_constitution_context()
    file_plan = [
        {
            "path": str(path),
            "operation": "inspect-before-edit",
            "reason": _file_reason(str(path), mission),
            "risk": _file_risk(str(path)),
        }
        for path in files
    ]
    ai_result = invoke_ai(
        {
            "system": "You are a cautious repository file planner. Do not generate code. Return file-level intent and validation notes only. Follow the runtime Constitution.",
            "prompt": "Create a file modification plan.\n" + json.dumps({"mission": mission, "file_plan": file_plan, "runtime_constitution": constitution}, sort_keys=True),
            "model": payload.get("model"),
        }
    )
    return {
        "company": "AI Software Factory",
        "product": "Repository Intelligence",
        "milestone": "GCP-09",
        "status": "file-plan-created" if ai_result.get("status") == "completed" else f"file-plan-{ai_result.get('status', 'unknown')}",
        "file_plan_id": plan_id,
        "mission_id": mission["mission_id"],
        "runtime_constitution": constitution,
        "file_plan": file_plan,
        "validation_gates": [
            "python -m compileall app",
            "python -m app.platform.api_contract",
            "bash infra/scripts/gate.sh",
            "PR Validation workflow must pass before merge",
        ],
        "ai_guidance": ai_result,
        "next_step": "GCP-10 Autonomous Code Generation",
    }


def _select_files(mission: dict[str, Any]) -> list[str]:
    text = " ".join(str(value).lower() for value in mission.values())
    selected = set(CORE_REPOSITORY_AREAS["api"])
    rules = {
        "runtime": ["runtime", "openai", "ai provider", "secret", "worker"],
        "engineering_worker": ["engineering", "blueprint", "pr plan", "autonomous"],
        "mission_execution": ["mission", "execution", "plan", "start"],
        "founder_approval": ["approval", "approve", "reject", "governance"],
        "proposal_generator": ["proposal", "generate"],
        "founder_workspace": ["founder", "request", "workspace"],
        "ci": ["ci", "validation", "test", "gate"],
        "deploy": ["deploy", "cloud run", "docker"],
        "constitution": ["constitution", "governance", "policy", "runtime binding"],
    }
    for area, tokens in rules.items():
        if any(token in text for token in tokens):
            selected.update(CORE_REPOSITORY_AREAS[area])
    return sorted(selected)


def _normalize_mission(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("mission") if isinstance(payload.get("mission"), dict) else payload
    return {
        "mission_id": str(source.get("mission_id") or source.get("id") or "MISSION-UNSPECIFIED").strip(),
        "title": str(source.get("mission_title") or source.get("title") or "Repository intelligence mission").strip(),
        "goal": str(source.get("goal") or source.get("description") or "Select repository context for implementation.").strip(),
        "context": str(source.get("current_context") or source.get("context") or "").strip(),
    }


def _area_purpose(area: str) -> str:
    return {
        "api": "FastAPI routing and API contract surface.",
        "runtime": "AI provider, Secret Manager contract, and runtime endpoints.",
        "engineering_worker": "Autonomous blueprint and PR planning capabilities.",
        "mission_execution": "Mission planning, start, and execution bridge.",
        "founder_approval": "Founder approval and rejection governance.",
        "proposal_generator": "Proposal generation from founder requests.",
        "founder_workspace": "Founder-facing request intake.",
        "ci": "Automated validation gates.",
        "deploy": "Cloud Run deployment and container runtime.",
        "constitution": "Runtime governance and policy binding.",
    }.get(area, "Repository area.")


def _file_reason(path: str, mission: dict[str, Any]) -> str:
    if path.endswith("server.py"):
        return "Endpoint wiring is usually required for platform capabilities."
    if path.endswith("api_contract.py"):
        return "API contract must include any new endpoint."
    if "constitution" in path:
        return "Mission relates to runtime governance and Constitution binding."
    if "runtime" in path:
        return "Mission relates to runtime or AI provider behavior."
    if "autonomous_engineering" in path:
        return "Mission relates to engineering-worker planning."
    return f"Selected based on mission goal: {mission['goal']}"


def _file_risk(path: str) -> str:
    if path.endswith("server.py") or path.endswith("api_contract.py"):
        return "medium"
    if path.startswith(".github") or path.startswith("infra"):
        return "high"
    return "low"


def _id(prefix: str, timestamp: str, data: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}-{timestamp[:10].replace('-', '')}-{digest}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
