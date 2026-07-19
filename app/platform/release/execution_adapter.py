from __future__ import annotations

import os
from typing import Any, Dict

import requests

from app.platform.governance_authorization.service import authorize_governed_action, record_governed_outcome


API = "https://api.github.com/repos/tehkst/ai-app-builder-dev"
READ_ONLY = {"compare_releases", "release_notes", "release_history"}


def execute_release_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    action = str(payload.get("action") or "").strip()
    token = os.getenv("GITHUB_TOKEN")
    if not token: return {"status": "blocked", "error": "GitHub credential is not mounted."}
    request = _request(action, payload)
    if isinstance(request, str): return {"status": "blocked", "error": request}
    decision = authorize_governed_action(payload, "release_%s" % action, policy_context={"release_gates": bool(payload.get("release_gates_passed", action in READ_ONLY)), "platform_state": True, "durable_approval_required": action not in READ_ONLY})
    if action not in READ_ONLY and not decision.get("allowed"): return {"status": "blocked", "authorization": decision, "error": decision.get("reason")}
    method, path, body = request
    response = requests.request(method, API + path, headers={"Authorization": "Bearer %s" % token, "Accept": "application/vnd.github+json"}, json=body, timeout=20)
    data = response.json() if response.content else {}
    result = {"status": "completed" if response.ok else "failed", "action": action, "status_code": response.status_code, "tag_name": data.get("tag_name") if isinstance(data, dict) else None, "release_url": data.get("html_url") if isinstance(data, dict) else None, "result": data if action in READ_ONLY else None}
    result["governance_evidence"] = record_governed_outcome(payload, decision, result)
    return result


def release_capability_probe() -> Dict[str, Any]:
    return {"implemented": True, "configured": bool(os.getenv("GITHUB_TOKEN")), "detail": "GitHub Releases API"}


def _request(action: str, payload: Dict[str, Any]) -> Any:
    tag = str(payload.get("tag_name") or "")
    if action == "create_release": return "POST", "/releases", {"tag_name": tag, "target_commitish": payload.get("target_commitish") or "main", "name": payload.get("name") or tag, "body": payload.get("body") or "", "draft": bool(payload.get("draft")), "prerelease": bool(payload.get("prerelease"))}
    if action == "promote_release": return "PATCH", "/releases/%s" % payload.get("release_id"), {"draft": False, "prerelease": False}
    if action == "rollback_release": return "POST", "/releases", {"tag_name": tag, "target_commitish": payload.get("target_commitish"), "name": payload.get("name") or "Rollback %s" % tag, "body": payload.get("body") or "Governed rollback release"}
    if action == "compare_releases": return "GET", "/compare/%s...%s" % (payload.get("base"), payload.get("head")), None
    if action == "release_notes": return "POST", "/releases/generate-notes", {"tag_name": tag, "target_commitish": payload.get("target_commitish") or "main", "previous_tag_name": payload.get("previous_tag_name")}
    if action == "release_history": return "GET", "/releases", None
    if action == "version_tag": return "POST", "/git/refs", {"ref": "refs/tags/%s" % tag, "sha": payload.get("commit_sha")}
    return "Unsupported release action."
