from __future__ import annotations

import hashlib
import os
import base64
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional

import requests


SKILLS_ROOT = Path(__file__).resolve().parents[1] / "agents" / "skills"
GITHUB_API = "https://api.github.com"
REPOSITORY = "tehkst/ai-app-builder-dev"
_ACTIVE_SKILL_LOADS: Dict[str, Dict[str, Any]] = {}
_ACTIVE_SKILL_LOADS_LOCK = RLock()


def skill_path(agent_id: str) -> Path:
    safe_id = str(agent_id or "").strip()
    if not safe_id or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for character in safe_id):
        raise ValueError("Invalid worker identity")
    return SKILLS_ROOT / safe_id / "skills.md"


def read_skill_document(agent_id: str) -> Dict[str, Any]:
    path = skill_path(agent_id)
    if not path.is_file():
        return {
            "available": False,
            "agent_id": agent_id,
            "source": str(path.relative_to(path.parents[5])),
            "content": None,
            "version": None,
            "validation": {"valid": False, "errors": ["Operational skill document is not available."]},
        }
    content = path.read_text(encoding="utf-8")
    validation = validate_skill_document(content)
    return {
        "available": True,
        "agent_id": agent_id,
        "source": str(path.relative_to(path.parents[5])),
        "content": content,
        "version": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "validation": validation,
    }


def validate_skill_document(content: str) -> Dict[str, Any]:
    errors = []
    value = str(content or "")
    if len(value.strip()) < 80:
        errors.append("The skill document is empty or too short.")
    if not value.lstrip().startswith("# "):
        errors.append("The skill document must begin with a level-one heading.")
    for heading in ("## Purpose", "## Capabilities", "## Operating boundaries"):
        if heading not in value:
            errors.append("Missing required section: %s" % heading)
    return {"valid": not errors, "errors": errors}


def inject_operational_skills(task: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
    enriched = dict(task or {})
    payload = dict(enriched.get("input_payload") or {})
    document = read_skill_document(agent_id)
    diagnostic = {
        "worker_id": agent_id,
        "source": document.get("source"),
        "version": document.get("version"),
        "loaded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "release_revision": os.getenv("K_REVISION") or os.getenv("BUILD_SHA"),
        "load_result": "loaded" if document.get("validation", {}).get("valid") else "invalid",
    }
    with _ACTIVE_SKILL_LOADS_LOCK:
        _ACTIVE_SKILL_LOADS[agent_id] = diagnostic
    payload["operational_skills"] = {
        **diagnostic,
        "content": document.get("content") if document.get("validation", {}).get("valid") else None,
        "loaded": bool(document.get("available") and document.get("validation", {}).get("valid")),
    }
    enriched["input_payload"] = payload
    return enriched


def active_skill_diagnostic(agent_id: str) -> Dict[str, Any]:
    with _ACTIVE_SKILL_LOADS_LOCK:
        active = dict(_ACTIVE_SKILL_LOADS.get(agent_id) or {})
    if active:
        return active
    document = read_skill_document(agent_id)
    return {
        "worker_id": agent_id,
        "source": document.get("source"),
        "version": document.get("version"),
        "loaded_at": None,
        "release_revision": os.getenv("K_REVISION") or os.getenv("BUILD_SHA"),
        "load_result": "not-yet-loaded",
    }


def skill_history(agent_id: str, limit: int = 20) -> Dict[str, Any]:
    path = str(skill_path(agent_id).relative_to(skill_path(agent_id).parents[5]))
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {"available": False, "items": [], "reason": "GitHub repository evidence is unavailable."}
    response = requests.get(
        "%s/repos/%s/commits" % (GITHUB_API, REPOSITORY),
        headers=_headers(token),
        params={"path": path, "per_page": max(1, min(limit, 50))},
        timeout=8,
    )
    if response.status_code != 200:
        return {"available": False, "items": [], "reason": "GitHub history request failed safely."}
    items = []
    for item in response.json():
        commit = item.get("commit") or {}
        author = commit.get("author") or {}
        items.append({
            "version": item.get("sha"),
            "summary": str(commit.get("message") or "").splitlines()[0],
            "actor": author.get("name"),
            "recorded_at": author.get("date"),
            "source_url": item.get("html_url"),
        })
    return {"available": True, "items": items, "source": "GitHub commit history"}


def read_skill_version(agent_id: str, version: str) -> Dict[str, Any]:
    path = str(skill_path(agent_id).relative_to(skill_path(agent_id).parents[5]))
    token = os.getenv("GITHUB_TOKEN")
    if not token or not version:
        return {"available": False, "reason": "GitHub version evidence is unavailable."}
    response = requests.get(
        "%s/repos/%s/contents/%s" % (GITHUB_API, REPOSITORY, path),
        headers=_headers(token),
        params={"ref": version},
        timeout=8,
    )
    if response.status_code != 200:
        return {"available": False, "reason": "The selected skill version could not be read."}
    body = response.json()
    try:
        content = base64.b64decode(str(body.get("content") or "")).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return {"available": False, "reason": "The selected skill version is unreadable."}
    return {
        "available": True,
        "version": version,
        "content": content,
        "validation": validate_skill_document(content),
        "source": path,
    }


def _headers(token: str) -> Dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer %s" % token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ai-software-factory-organisation-console",
    }
