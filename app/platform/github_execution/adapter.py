from __future__ import annotations

import os
from typing import Any, Dict

import requests

from app.platform.governance_authorization.service import authorize_governed_action, record_governed_outcome


API = "https://api.github.com"
REPOSITORY = "tehkst/ai-app-builder-dev"
READ_ONLY = {"workflow_inspection"}


def execute_github_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    action = str(payload.get("action") or "").strip()
    token = os.getenv("GITHUB_TOKEN")
    if not token: return {"status": "blocked", "error": "GitHub credential is not mounted.", "token_visible": False}
    request = _request(action, payload)
    if isinstance(request, str): return {"status": "blocked", "error": request, "token_visible": False}
    decision = authorize_governed_action(payload, "github_%s" % action, policy_context={"platform_state": True, "durable_approval_required": action not in READ_ONLY})
    if action not in READ_ONLY and not decision.get("allowed"): return {"status": "blocked", "authorization": decision, "error": decision.get("reason"), "token_visible": False}
    method, path, body = request
    response = requests.request(method, "%s/repos/%s%s" % (API, REPOSITORY, path), headers={"Authorization": "Bearer %s" % token, "Accept": "application/vnd.github+json"}, json=body, timeout=20)
    data = response.json() if response.content else {}
    result = {"status": "completed" if response.ok else "failed", "action": action, "status_code": response.status_code, "repository": REPOSITORY, "result": _safe_result(data), "token_visible": False}
    result["governance_evidence"] = record_governed_outcome(payload, decision, result)
    return result


def github_capability_probe() -> Dict[str, Any]:
    return {"implemented": True, "configured": bool(os.getenv("GITHUB_TOKEN")), "detail": "GitHub credential mounted" if os.getenv("GITHUB_TOKEN") else "GitHub credential missing"}


def _request(action: str, payload: Dict[str, Any]) -> Any:
    pr = str(payload.get("pr_number") or "")
    if action == "update_pr": return "PATCH", "/pulls/%s" % pr, {key: payload[key] for key in ("title", "body", "state", "base") if key in payload}
    if action in {"review_pr", "request_changes", "approve_pr"}:
        event = {"review_pr": "COMMENT", "request_changes": "REQUEST_CHANGES", "approve_pr": "APPROVE"}[action]
        return "POST", "/pulls/%s/reviews" % pr, {"body": str(payload.get("body") or ""), "event": event}
    if action in {"close_pr", "reopen_pr"}: return "PATCH", "/pulls/%s" % pr, {"state": "closed" if action == "close_pr" else "open"}
    if action == "assign_reviewers": return "POST", "/pulls/%s/requested_reviewers" % pr, {"reviewers": payload.get("reviewers") or [], "team_reviewers": payload.get("team_reviewers") or []}
    if action == "labels": return "POST", "/issues/%s/labels" % pr, {"labels": payload.get("labels") or []}
    if action == "milestones": return "PATCH", "/issues/%s" % pr, {"milestone": payload.get("milestone")}
    if action == "workflow_inspection": return "GET", "/actions/runs", None
    return "Unsupported GitHub action."


def _safe_result(data: Any) -> Any:
    if not isinstance(data, dict): return data
    allowed = ("id", "number", "state", "html_url", "message", "total_count", "workflow_runs")
    return {key: data.get(key) for key in allowed if key in data}
