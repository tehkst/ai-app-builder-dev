from __future__ import annotations

import os
from typing import Any

import requests

from app.platform.auth.service import require_founder
from app.platform.governance_authorization.service import authorize_governed_action, record_governed_outcome
from app.platform.github_execution.pr_lifecycle import resolve_pr_mission_identity

APPROVAL_PHRASE = "I APPROVE PR MERGE"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
REPOSITORY_FULL_NAME = "tehkst/ai-app-builder-dev"
VALID_MERGE_METHODS = {"squash", "merge", "rebase"}


def build_github_merge_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Founder-approved Pull Request Merge",
        "status": "ready" if bool(os.getenv(GITHUB_TOKEN_ENV)) else "awaiting-github-token",
        "repository": REPOSITORY_FULL_NAME,
        "github_token_present": bool(os.getenv(GITHUB_TOKEN_ENV)),
        "github_token_visible": False,
        "required_approval_phrase": APPROVAL_PHRASE,
        "capabilities": ["merge-preview", "founder-approved-pr-merge"],
        "governance": {
            "founder_token_required": True,
            "live_execution_required": True,
            "approval_phrase_required": True,
            "base_branch_required": "main",
            "deployment": False,
            "cloud_run": False,
            "traffic_shift": False,
            "file_writes": False,
        },
        "endpoints": {
            "summary": "GET /mission-control/github-merge",
            "preview": "POST /mission-control/github-merge/preview",
            "execute": "POST /mission-control/github-merge/execute",
        },
    }


def preview_github_merge(payload: dict[str, Any]) -> dict[str, Any]:
    auth = require_founder(payload)
    pr_number = _parse_pr_number(payload.get("pr_number"))
    if not auth.get("authorized"):
        return _blocked(pr_number, "Founder token is invalid or missing.")
    if pr_number is None:
        return _blocked(None, "pr_number must be a positive integer.")
    token = os.getenv(GITHUB_TOKEN_ENV)
    if not token:
        return _blocked(pr_number, "GITHUB_TOKEN is not mounted.")
    pr, checks_summary, checks_error = _read_pr_status(pr_number, token)
    if pr.get("status") == "blocked":
        return pr
    return _preview_response(pr, checks_summary, checks_error)


def execute_github_merge(payload: dict[str, Any]) -> dict[str, Any]:
    pr_number = _parse_pr_number(payload.get("pr_number"))
    merge_method = str(payload.get("merge_method") or "squash").strip().lower()
    errors: list[str] = []
    decision = authorize_governed_action(payload, "merge_pr", required_approval_phrase=APPROVAL_PHRASE, policy_context={"mission_state": True, "platform_state": bool(os.getenv(GITHUB_TOKEN_ENV))})
    if not decision.get("allowed"):
        errors.append(str(decision.get("reason") or "Governance authorization denied."))
    if pr_number is None:
        errors.append("pr_number must be a positive integer.")
    if merge_method not in VALID_MERGE_METHODS:
        errors.append("merge_method must be squash, merge, or rebase.")
    if payload.get("live_execution") is not True:
        errors.append("live_execution must be true.")
    if payload.get("approval_phrase") != APPROVAL_PHRASE:
        errors.append("approval_phrase must exactly match the required approval phrase.")
    token = os.getenv(GITHUB_TOKEN_ENV)
    if not token:
        errors.append("GITHUB_TOKEN is not mounted.")
    if errors:
        return _blocked(pr_number, " ".join(errors))

    pr, checks_summary, checks_error = _read_pr_status(int(pr_number), str(token))
    if pr.get("status") == "blocked":
        return pr
    gate_error = _merge_gate_error(pr)
    if gate_error:
        blocked = _preview_response(pr, checks_summary, checks_error)
        blocked["status"] = "merge-blocked"
        blocked["recommended_action"] = gate_error
        return blocked

    try:
        merge_result = _github_put(f"/pulls/{pr_number}/merge", str(token), {"merge_method": merge_method})
    except RuntimeError as exc:
        blocked = _preview_response(pr, checks_summary, checks_error)
        blocked["status"] = "merge-failed"
        blocked["recommended_action"] = str(exc)
        return blocked

    response = {
        "status": "pr-merged",
        "repository": REPOSITORY_FULL_NAME,
        "pr_number": pr_number,
        "pr_url": pr.get("html_url"),
        "title": pr.get("title"),
        "merge_method": merge_method,
        "merge_commit_sha": merge_result.get("sha"),
        "merged": True,
        "message": merge_result.get("message"),
        "github_token_visible": False,
        "deployment": False,
        "cloud_run": False,
        "traffic_shift": False,
        "file_writes": False,
        "founder_approval_required": True,
        **resolve_pr_mission_identity(pr, payload.get("execution_metadata")),
        "authorization": decision,
    }
    response["governance_evidence"] = record_governed_outcome(payload, decision, response)
    from app.platform.operating_console.delivery_link import link_authority_result

    return link_authority_result(
        payload,
        response,
        authority="approved_merge",
        event_key=merge_result.get("sha") or pr_number,
    )


def _read_pr_status(pr_number: int, token: str) -> tuple[dict[str, Any], Any, str | None]:
    try:
        pr = _github_get(f"/pulls/{pr_number}", token)
    except RuntimeError as exc:
        return _blocked(pr_number, str(exc)), "unknown", None
    sha = str(((pr.get("head") or {}).get("sha")) or "")
    checks_summary: Any = "unknown"
    checks_error = None
    if sha:
        try:
            checks = _github_get(f"/commits/{sha}/check-runs", token, params={"per_page": 100})
            checks_summary = _summarize_checks(checks.get("check_runs") or [])
        except RuntimeError as exc:
            checks_error = str(exc)
    return pr, checks_summary, checks_error


def _preview_response(pr: dict[str, Any], checks_summary: Any, checks_error: str | None) -> dict[str, Any]:
    return {
        "status": "merge-preview-ready",
        "repository": REPOSITORY_FULL_NAME,
        "pr_number": pr.get("number"),
        "pr_url": pr.get("html_url"),
        "title": pr.get("title"),
        "state": pr.get("state"),
        "mergeable": pr.get("mergeable"),
        "merged": bool(pr.get("merged")),
        "merge_commit_sha": pr.get("merge_commit_sha"),
        "head_branch": ((pr.get("head") or {}).get("ref")),
        "base_branch": ((pr.get("base") or {}).get("ref")),
        "checks_summary": checks_summary,
        "checks_error": checks_error,
        "recommended_action": _recommended_action(pr, checks_summary),
        "github_token_visible": False,
        "deployment": False,
        "cloud_run": False,
        "traffic_shift": False,
        "file_writes": False,
        "founder_approval_required": True,
        **resolve_pr_mission_identity(pr),
    }


def _merge_gate_error(pr: dict[str, Any]) -> str | None:
    if bool(pr.get("merged")):
        return "PR is already merged."
    if pr.get("state") != "open":
        return "PR is closed and cannot be merged by Mission Control."
    if ((pr.get("base") or {}).get("ref")) != "main":
        return "PR base branch must be main."
    if pr.get("mergeable") is not True:
        return "PR is not currently mergeable. Resolve conflicts or re-check after GitHub recalculates mergeability."
    return None


def _recommended_action(pr: dict[str, Any], checks_summary: Any) -> str:
    gate_error = _merge_gate_error(pr)
    if gate_error:
        return gate_error
    if checks_summary == "unknown":
        return "PR is mergeable, but checks could not be read. Review GitHub checks before live merge."
    if checks_summary.get("overall") == "failing":
        return "Fix failing checks before founder-approved merge."
    if checks_summary.get("overall") == "pending":
        return "Wait for checks to finish before founder-approved merge."
    return "Ready for explicit founder-approved merge."


def _parse_pr_number(value: Any) -> int | None:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _github_get(path: str, token: str, params: dict[str, Any] | None = None) -> Any:
    return _github_request("GET", path, token, params=params)


def _github_put(path: str, token: str, payload: dict[str, Any]) -> Any:
    return _github_request("PUT", path, token, json_payload=payload)


def _github_request(method: str, path: str, token: str, params: dict[str, Any] | None = None, json_payload: dict[str, Any] | None = None) -> Any:
    try:
        response = requests.request(
            method,
            f"{GITHUB_API_BASE}/repos/{REPOSITORY_FULL_NAME}{path}",
            params=params,
            json=json_payload,
            timeout=30,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "mission-control-approved-merge",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
    except requests.RequestException as exc:
        raise RuntimeError("GitHub request failed.") from exc
    if response.status_code >= 400:
        raise RuntimeError(f"GitHub request failed: {_safe_response_error(response)}")
    return response.json()


def _summarize_checks(checks: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(checks)
    passing = sum(1 for item in checks if item.get("conclusion") in {"success", "neutral", "skipped"})
    failing = sum(1 for item in checks if item.get("conclusion") in {"failure", "timed_out", "cancelled", "action_required"})
    pending = sum(1 for item in checks if item.get("status") in {"queued", "in_progress", "pending"} or item.get("conclusion") is None)
    overall = "pending" if pending else "passing"
    if failing:
        overall = "failing"
    if total == 0:
        overall = "not-found"
    return {"overall": overall, "total": total, "passing": passing, "failing": failing, "pending": pending}


def _safe_response_error(response: requests.Response) -> str:
    try:
        payload = response.json()
        message = str(payload.get("message") or f"HTTP {response.status_code}")
    except ValueError:
        message = f"HTTP {response.status_code}"
    token = os.getenv(GITHUB_TOKEN_ENV)
    return message.replace(token, "[redacted]") if token else message


def _blocked(pr_number: int | None, reason: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "repository": REPOSITORY_FULL_NAME,
        "pr_number": pr_number,
        "recommended_action": reason,
        "github_token_visible": False,
        "deployment": False,
        "cloud_run": False,
        "traffic_shift": False,
        "file_writes": False,
        "founder_approval_required": True,
    }
