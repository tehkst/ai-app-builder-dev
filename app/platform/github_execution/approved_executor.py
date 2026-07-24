from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.platform.auth.service import require_founder
from app.platform.governance_authorization.service import authorize_governed_action, record_governed_outcome
from app.platform.patch_application.service import REPOSITORY_FULL_NAME

APPROVAL_PHRASE = "I APPROVE GITHUB EXECUTION"
BASE_BRANCH = "main"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
REPO_ROOT = Path(__file__).resolve().parents[3]


class ApprovedExecutionError(RuntimeError):
    def __init__(self, message: str, evidence: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.evidence = evidence or {}


def build_approved_github_execution_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Approved GitHub Write + PR Engine",
        "status": "ready" if bool(os.getenv(GITHUB_TOKEN_ENV)) else "awaiting-github-token",
        "repository": REPOSITORY_FULL_NAME,
        "base_branch": BASE_BRANCH,
        "github_token_present": bool(os.getenv(GITHUB_TOKEN_ENV)),
        "github_token_visible": False,
        "mutation_enabled": False,
        "governance": _governance(),
        "endpoints": {
            "summary": "GET /mission-control/github-execution",
            "preview": "POST /mission-control/github-execution/preview",
            "execute": "POST /mission-control/github-execution/execute",
        },
    }


def preview_approved_github_execution(payload: dict[str, Any]) -> dict[str, Any]:
    auth = require_founder(payload)
    request, errors = _validate_request(payload)
    return {
        "company": "AI Software Factory",
        "product": "Approved GitHub Write + PR Engine",
        "status": "preview-ready" if auth.get("authorized") and not errors else "preview-blocked",
        "authorized": bool(auth.get("authorized")),
        "repository": REPOSITORY_FULL_NAME,
        "mission_id": request["mission_id"],
        "title": request["title"],
        "branch_name": request["branch_name"],
        "base_branch": BASE_BRANCH,
        "commit_message": request["commit_message"],
        "pr_title": request["pr_title"],
        "files_to_change": [
            {
                "path": item["path"],
                "operation": item["operation"],
                "bytes": len(str(item.get("content") or "").encode("utf-8")),
            }
            for item in request["file_changes"]
        ],
        "execution_gates": {
            "founder_token_valid": bool(auth.get("authorized")),
            "live_execution": bool(payload.get("live_execution") is True),
            "approval_phrase_valid": payload.get("approval_phrase") == APPROVAL_PHRASE,
            "github_token_present": bool(os.getenv(GITHUB_TOKEN_ENV)),
        },
        "writes_performed": False,
        "pull_request_created": False,
        "github_token_visible": False,
        "errors": errors,
    }


def execute_approved_github_execution(payload: dict[str, Any]) -> dict[str, Any]:
    request, errors = _validate_request(payload)
    decision = authorize_governed_action(payload, "create_pr", required_approval_phrase=APPROVAL_PHRASE, policy_context={"mission_state": bool(request["mission_id"]), "platform_state": bool(os.getenv(GITHUB_TOKEN_ENV))})
    gate_errors = list(errors)
    if not decision.get("allowed"):
        gate_errors.append(str(decision.get("reason") or "Governance authorization denied."))
    token = os.getenv(GITHUB_TOKEN_ENV)
    if not token:
        gate_errors.append("GITHUB_TOKEN is not mounted.")
    if gate_errors:
        return _blocked(request, gate_errors)

    try:
        result = _perform_execution(request, str(token))
    except ApprovedExecutionError as exc:
        response = {
            "company": "AI Software Factory",
            "product": "Approved GitHub Write + PR Engine",
            "status": "github-execution-failed",
            "repository": REPOSITORY_FULL_NAME,
            "mission_id": request["mission_id"],
            "branch_name": request["branch_name"],
            "commit": exc.evidence.get("commit"),
            "files_changed": exc.evidence.get("files_changed", []),
            "push_status": exc.evidence.get("push_status", "not-started"),
            "failed_stage": "pull_request_creation" if exc.evidence.get("push_status") == "completed" else "repository_execution",
            "error": str(exc),
            "github_token_visible": False,
            "merge": False,
            "deployment": False,
            "traffic_shift": False,
        }
        response["governance_evidence"] = record_governed_outcome(payload, decision, response)
        return response

    response = {
        "company": "AI Software Factory",
        "product": "Approved GitHub Write + PR Engine",
        "status": "pull-request-created",
        "repository": REPOSITORY_FULL_NAME,
        "mission_id": request["mission_id"],
        "branch_name": request["branch_name"],
        "commit": result["commit"],
        "files_changed": result["files_changed"],
        "pull_request_url": result["pull_request_url"],
        "pull_request_number": result["pull_request_number"],
        "github_token_visible": False,
        "merge": False,
        "deployment": False,
        "traffic_shift": False,
        "founder_approval_required_for_next_step": True,
        "authorization": decision,
    }
    response["governance_evidence"] = record_governed_outcome(payload, decision, response)
    from app.platform.operating_console.delivery_link import link_authority_result

    return link_authority_result(
        payload,
        response,
        authority="github_execution",
        event_key=result["pull_request_number"],
    )


def _validate_request(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    request = {
        "mission_id": str(payload.get("mission_id") or "MC-GH-EXEC-UNSPECIFIED").strip(),
        "title": str(payload.get("title") or "Approved GitHub execution").strip(),
        "branch_name": str(payload.get("branch_name") or "").strip(),
        "commit_message": str(payload.get("commit_message") or "").strip(),
        "pr_title": str(payload.get("pr_title") or "").strip(),
        "pr_body": str(payload.get("pr_body") or "").strip(),
        "file_changes": [],
    }
    errors: list[str] = []
    if not request["branch_name"]:
        errors.append("branch_name is required.")
    elif not _valid_branch_name(request["branch_name"]):
        errors.append("branch_name must be a safe feature branch and cannot be main or master.")
    if not request["commit_message"]:
        errors.append("commit_message is required.")
    if not request["pr_title"]:
        errors.append("pr_title is required.")

    raw_changes = payload.get("file_changes")
    if not isinstance(raw_changes, list) or not raw_changes:
        errors.append("file_changes must be a non-empty list.")
        return request, errors

    seen: set[str] = set()
    for index, item in enumerate(raw_changes, start=1):
        if not isinstance(item, dict):
            errors.append(f"file_changes[{index}] must be an object.")
            continue
        path = str(item.get("path") or "").strip()
        operation = str(item.get("operation") or "write").strip().lower()
        content = item.get("content")
        safe_path = _safe_relative_path(path)
        if not safe_path:
            errors.append(f"file_changes[{index}].path is unsafe or missing.")
            continue
        if safe_path in seen:
            errors.append(f"Duplicate file change path: {safe_path}.")
            continue
        if operation not in {"write", "create", "update", "modify", "delete"}:
            errors.append(f"file_changes[{index}].operation is unsupported.")
            continue
        normalized_operation = "delete" if operation == "delete" else "write"
        if normalized_operation == "write" and not isinstance(content, str):
            errors.append(f"file_changes[{index}].content must be a string.")
            continue
        seen.add(safe_path)
        request["file_changes"].append(
            {
                "path": safe_path,
                "operation": normalized_operation,
                "content": content if normalized_operation == "write" else None,
            }
        )
    return request, errors


def _valid_branch_name(branch: str) -> bool:
    if branch in {"main", "master"}:
        return False
    if branch.startswith(("-", "/", ".")) or branch.endswith(("/", ".", ".lock")):
        return False
    if ".." in branch or "@{" in branch or "\\" in branch:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9._/-]{3,120}", branch))


def _safe_relative_path(path: str) -> str | None:
    if not path or path.startswith("/") or "\\" in path:
        return None
    candidate = Path(path)
    if any(part in {"", ".", ".."} for part in candidate.parts):
        return None
    safe = candidate.as_posix()
    if safe == ".git" or safe.startswith(".git/"):
        return None
    resolved = (REPO_ROOT / safe).resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        return None
    return safe


def _perform_execution(request: dict[str, Any], token: str) -> dict[str, Any]:
    askpass = _write_askpass_script()
    env = _git_env(askpass)
    try:
        repo_url = f"https://github.com/{REPOSITORY_FULL_NAME}.git"
        _run(["git", "fetch", "--depth=1", repo_url, BASE_BRANCH], env)
        _run(["git", "checkout", "-B", request["branch_name"], "FETCH_HEAD"], env)
        changed_paths = _write_files(request["file_changes"])
        status = _run(["git", "status", "--porcelain", "--", *changed_paths], env).stdout.strip()
        if not status:
            raise ApprovedExecutionError("No file changes detected after writing approved files.")
        _run(["git", "add", "--", *changed_paths], env)
        _run(["git", "commit", "-m", request["commit_message"]], env)
        commit = _run(["git", "rev-parse", "HEAD"], env).stdout.strip()
        _run(["git", "push", "-u", repo_url, request["branch_name"]], env)
        try:
            pr = _create_pull_request(request, token)
        except ApprovedExecutionError as exc:
            raise ApprovedExecutionError(str(exc), {"commit": commit, "files_changed": changed_paths, "push_status": "completed"}) from exc
        return {"commit": commit, "files_changed": changed_paths, "pull_request_url": pr["url"], "pull_request_number": pr["number"]}
    finally:
        try:
            Path(askpass).unlink(missing_ok=True)
        except OSError:
            pass


def _write_files(file_changes: list[dict[str, Any]]) -> list[str]:
    paths: list[str] = []
    for item in file_changes:
        target = (REPO_ROOT / item["path"]).resolve()
        if item.get("operation") == "delete":
            if not target.is_file() or target.is_symlink():
                raise ApprovedExecutionError(
                    "Approved delete target is unavailable or unsafe."
                )
            target.unlink()
            paths.append(item["path"])
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(item["content"]), encoding="utf-8")
        paths.append(item["path"])
    return paths


def _create_pull_request(request: dict[str, Any], token: str) -> dict[str, Any]:
    owner, repo = REPOSITORY_FULL_NAME.split("/", 1)
    pr_body = _pr_body_with_mission_marker(request["pr_body"] or request["title"], request["mission_id"])
    body = json.dumps({
        "title": request["pr_title"],
        "head": request["branch_name"],
        "base": BASE_BRANCH,
        "body": pr_body,
    }).encode("utf-8")
    api_request = urllib.request.Request(
        f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls",
        data=body,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "mission-control-approved-github-execution",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(api_request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = _safe_http_error(exc)
        raise ApprovedExecutionError(f"GitHub pull request creation failed: {detail}") from exc
    except OSError as exc:
        raise ApprovedExecutionError("GitHub pull request creation failed.") from exc
    url = str(payload.get("html_url") or "").strip()
    if not url:
        raise ApprovedExecutionError("GitHub pull request response did not include a PR URL.")
    number = payload.get("number")
    if not isinstance(number, int) or number <= 0:
        raise ApprovedExecutionError("GitHub pull request response did not include a PR number.")
    return {"url": url, "number": number}


def _pr_body_with_mission_marker(body: str, mission_id: str) -> str:
    marker = f"Mission-ID: {mission_id}"
    lines = [line for line in body.splitlines() if not re.match(r"^\s*Mission-ID\s*:", line, re.IGNORECASE)]
    content = "\n".join(lines).strip()
    return f"{content}\n\n{marker}" if content else marker


def _write_askpass_script() -> str:
    handle = tempfile.NamedTemporaryFile("w", delete=False, prefix="mc-gh-askpass-", suffix=".sh")
    with handle:
        handle.write("#!/bin/sh\ncase \"$1\" in\n*Username*) echo \"x-access-token\" ;;\n*Password*) printf \"%s\" \"$GITHUB_TOKEN\" ;;\n*) echo \"\" ;;\nesac\n")
    os.chmod(handle.name, 0o700)
    return handle.name


def _git_env(askpass: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "GIT_ASKPASS": askpass,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "AI Software Factory Mission Control",
        "GIT_AUTHOR_EMAIL": "mission-control@ai-software-factory.local",
        "GIT_COMMITTER_NAME": "AI Software Factory Mission Control",
        "GIT_COMMITTER_EMAIL": "mission-control@ai-software-factory.local",
    })
    return env


def _run(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=REPO_ROOT, env=env, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise ApprovedExecutionError(f"Git command failed: {_scrub(result.stderr or result.stdout)}")
    return result


def _safe_http_error(exc: urllib.error.HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        message = str(payload.get("message") or f"HTTP {exc.code}")
    except Exception:
        message = f"HTTP {exc.code}"
    return _scrub(message)


def _scrub(value: str) -> str:
    token = os.getenv(GITHUB_TOKEN_ENV)
    return value.replace(token, "[redacted]") if token else value


def _blocked(request: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Approved GitHub Write + PR Engine",
        "status": "blocked",
        "repository": REPOSITORY_FULL_NAME,
        "mission_id": request["mission_id"],
        "branch_name": request["branch_name"],
        "errors": errors,
        "writes_performed": False,
        "pull_request_created": False,
        "github_token_visible": False,
        "governance": _governance(),
    }


def _governance() -> dict[str, Any]:
    return {
        "direct_main_writes": False,
        "founder_token_required": True,
        "live_execution_required": True,
        "approval_phrase_required": APPROVAL_PHRASE,
        "approved_files_only": True,
        "token_exposed": False,
        "merge": False,
        "deployment": False,
        "traffic_shift": False,
        "founder_approval_required": True,
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
