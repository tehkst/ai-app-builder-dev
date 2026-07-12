from __future__ import annotations

import os
import re
from typing import Any

import requests

from app.platform.auth.service import require_founder

GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
REPOSITORY_FULL_NAME = "tehkst/ai-app-builder-dev"


def build_github_pr_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Pull Request Lifecycle and CI Monitoring",
        "status": "ready" if bool(os.getenv(GITHUB_TOKEN_ENV)) else "awaiting-github-token",
        "repository": REPOSITORY_FULL_NAME,
        "github_token_present": bool(os.getenv(GITHUB_TOKEN_ENV)),
        "github_token_visible": False,
        "capabilities": ["pr-inspection", "changed-files", "checks-monitoring", "recommended-next-action"],
        "governance": {
            "merge": False,
            "deployment": False,
            "file_writes": False,
            "traffic_shift": False,
            "founder_approval_required": True,
        },
        "endpoints": {
            "summary": "GET /mission-control/github-pr",
            "status": "POST /mission-control/github-pr/status",
        },
    }


def get_github_pr_status(payload: dict[str, Any]) -> dict[str, Any]:
    auth = require_founder(payload)
    pr_number = _parse_pr_number(payload.get("pr_number"))
    token = os.getenv(GITHUB_TOKEN_ENV)
    if not auth.get("authorized"):
        return _blocked(pr_number, "Founder token is invalid or missing.")
    if pr_number is None:
        return _blocked(None, "pr_number must be a positive integer.")
    if not token:
        return _blocked(pr_number, "GITHUB_TOKEN is not mounted.")

    try:
        pr = _github_get(f"/pulls/{pr_number}", token)
        files = _github_get(f"/pulls/{pr_number}/files", token, params={"per_page": 100})
    except RuntimeError as exc:
        return _blocked(pr_number, str(exc))

    sha = str(((pr.get("head") or {}).get("sha")) or "")
    checks: list[dict[str, Any]] = []
    checks_summary: Any = "unknown"
    checks_error = None
    if sha:
        try:
            checks_payload = _github_get(f"/commits/{sha}/check-runs", token, params={"per_page": 100})
            checks = _normalize_checks(checks_payload)
            checks_summary = _summarize_checks(checks)
        except RuntimeError as exc:
            checks_error = str(exc)
    result = {
        "status": "pr-status-ready",
        "repository": REPOSITORY_FULL_NAME,
        "pr_number": pr_number,
        "pr_url": pr.get("html_url"),
        "title": pr.get("title"),
        "state": pr.get("state"),
        "merged": bool(pr.get("merged")),
        "mergeable": pr.get("mergeable"),
        "head_branch": ((pr.get("head") or {}).get("ref")),
        "base_branch": ((pr.get("base") or {}).get("ref")),
        "changed_files": pr.get("changed_files"),
        "additions": pr.get("additions"),
        "deletions": pr.get("deletions"),
        "checks_summary": checks_summary,
        "checks": checks,
        "checks_error": checks_error,
        "recommended_action": _recommended_action(pr, checks_summary),
        "founder_approval_required": True,
        "github_token_visible": False,
        "merge": False,
        "deployment": False,
        "file_writes": False,
        "traffic_shift": False,
        "files": [{"filename": item.get("filename"), "status": item.get("status"), "additions": item.get("additions"), "deletions": item.get("deletions")} for item in files],
    }
    result.update(resolve_pr_mission_identity(pr, payload.get("execution_metadata")))
    return result


def resolve_pr_mission_identity(pr: dict[str, Any], execution_metadata: Any = None) -> dict[str, Any]:
    candidates: list[dict[str, str]] = []
    body_matches = re.findall(r"(?im)^\s*Mission-ID\s*:\s*(MISSION-[A-Za-z0-9][A-Za-z0-9-]*)\s*$", str(pr.get("body") or ""))
    candidates.extend({"mission_id": value, "source": "pr-body-marker", "evidence": f"Mission-ID: {value}"} for value in body_matches)
    if isinstance(execution_metadata, dict):
        value = str(execution_metadata.get("mission_id") or "").strip()
        if _canonical_mission_id(value):
            candidates.append({"mission_id": value, "source": "execution-metadata", "evidence": "Structured GitHub execution metadata"})
    head = str(((pr.get("head") or {}).get("ref")) or "")
    title = str(pr.get("title") or "")
    for source, text in (("head-branch", head), ("pr-title", title)):
        for value in re.findall(r"MISSION-[A-Za-z0-9][A-Za-z0-9-]*", text, re.IGNORECASE):
            normalized = value.upper()
            if _canonical_mission_id(normalized):
                candidates.append({"mission_id": normalized, "source": source, "evidence": text})
    unique = {item["mission_id"] for item in candidates}
    if len(unique) > 1:
        return {"mission_id": None, "mission_resolution_status": "ambiguous", "mission_resolution_source": None, "mission_resolution_evidence": candidates}
    if not candidates:
        return {"mission_id": None, "mission_resolution_status": "unresolved", "mission_resolution_source": None, "mission_resolution_evidence": []}
    selected = next(item for source in ("pr-body-marker", "execution-metadata", "head-branch", "pr-title") for item in candidates if item["source"] == source)
    return {"mission_id": selected["mission_id"], "mission_resolution_status": "resolved", "mission_resolution_source": selected["source"], "mission_resolution_evidence": candidates}


def _canonical_mission_id(value: str) -> bool:
    return bool(re.fullmatch(r"MISSION-[A-Z0-9][A-Z0-9-]*", value))


def _parse_pr_number(value: Any) -> int | None:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _github_get(path: str, token: str, params: dict[str, Any] | None = None) -> Any:
    url = f"{GITHUB_API_BASE}/repos/{REPOSITORY_FULL_NAME}{path}"
    try:
        response = requests.get(
            url,
            params=params,
            timeout=30,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "mission-control-pr-lifecycle",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
    except requests.RequestException as exc:
        raise RuntimeError("GitHub read failed.") from exc
    if response.status_code >= 400:
        raise RuntimeError(f"GitHub read failed: {_safe_response_error(response)}")
    return response.json()


def _normalize_checks(checks_payload: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for item in checks_payload.get("check_runs") or []:
        checks.append({
            "name": item.get("name"),
            "type": "check_run",
            "status": item.get("status"),
            "conclusion": item.get("conclusion"),
            "url": item.get("html_url"),
        })
    return checks


def _summarize_checks(checks: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(checks)
    passing = sum(1 for item in checks if item.get("conclusion") in {"success", "neutral", "skipped"} or item.get("status") == "success")
    failing = sum(1 for item in checks if item.get("conclusion") in {"failure", "timed_out", "cancelled", "action_required"} or item.get("status") in {"failure", "error"})
    pending = sum(1 for item in checks if item.get("status") in {"queued", "in_progress", "pending", "expected"} or item.get("conclusion") is None)
    overall = "pending" if pending else "passing"
    if failing:
        overall = "failing"
    if total == 0:
        overall = "not-found"
    return {"overall": overall, "total": total, "passing": passing, "failing": failing, "pending": pending}


def _recommended_action(pr: dict[str, Any], checks_summary: Any) -> str:
    if pr.get("merged"):
        return "PR is already merged. No Mission Control merge or deployment action will run."
    if pr.get("state") != "open":
        return "PR is not open. Review manually before any follow-up."
    if pr.get("mergeable") is False:
        return "Resolve merge conflicts before founder approval."
    if checks_summary == "unknown":
        return "Checks could not be read. Review CI in GitHub, then re-check PR status."
    if checks_summary["overall"] == "failing":
        return "Fix failing checks, then re-check PR status."
    if checks_summary["overall"] == "pending":
        return "Wait for CI/checks to finish, then re-check PR status."
    if pr.get("mergeable") is True and checks_summary["overall"] in {"passing", "not-found"}:
        return "Ready for founder review. Merge and deployment remain manual."
    return "GitHub is still calculating mergeability. Re-check shortly."


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
        "pr_url": None,
        "title": None,
        "state": None,
        "merged": False,
        "mergeable": None,
        "head_branch": None,
        "base_branch": None,
        "changed_files": 0,
        "additions": 0,
        "deletions": 0,
        "checks_summary": {"overall": "blocked", "total": 0, "passing": 0, "failing": 0, "pending": 0},
        "checks": [],
        "recommended_action": reason,
        "founder_approval_required": True,
        "github_token_visible": False,
        "merge": False,
        "deployment": False,
        "file_writes": False,
        "traffic_shift": False,
        "mission_id": None,
        "mission_resolution_status": "unresolved",
        "mission_resolution_source": None,
        "mission_resolution_evidence": [],
    }
