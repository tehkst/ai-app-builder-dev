from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any

from app.platform.auth.service import require_founder
from app.platform.governance_authorization.service import authorize_governed_action, record_governed_outcome

APPROVAL_PHRASE = "I APPROVE CLOUD RUN ROLLBACK"
DEFAULT_PROJECT_ID = "ai-software-factory-500910"
DEFAULT_REGION = "asia-southeast1"
DEFAULT_SERVICE_NAME = "ai-software-factory-production"


def build_cloud_run_rollback_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Founder-approved Rollback",
        "status": "ready",
        "service_name": DEFAULT_SERVICE_NAME,
        "region": DEFAULT_REGION,
        "project_id": DEFAULT_PROJECT_ID,
        "required_approval_phrase": APPROVAL_PHRASE,
        "governance": {
            "founder_token_required": True,
            "live_execution_required": True,
            "approval_phrase_required": True,
            "deployment": False,
            "github_mutation": False,
            "pr_merge": False,
            "secrets_exposed": False,
        },
        "endpoints": {
            "summary": "GET /mission-control/rollback",
            "preview": "POST /mission-control/rollback/preview",
            "execute": "POST /mission-control/rollback/execute",
        },
    }


def preview_cloud_run_rollback(payload: dict[str, Any]) -> dict[str, Any]:
    request = _rollback_request(payload)
    auth = require_founder(payload)
    if not auth.get("authorized"):
        return _blocked(request, "Founder token is invalid or missing.")
    state = _read_service_state(request)
    target = request["target_revision"] or _recommended_revision(state)
    return {
        "status": "rollback-preview-ready",
        "service_name": request["service_name"],
        "region": request["region"],
        "project_id": request["project_id"],
        "current_active_revision": state["current_active_revision"],
        "target_revision": target,
        "recommended_target_revision": _recommended_revision(state),
        "recent_revisions": state["recent_revisions"],
        "current_traffic": state["current_traffic"],
        "read_errors": state["errors"],
        "traffic_shift_performed": False,
        "deployment": False,
        "github_mutation": False,
        "pr_merge": False,
        "secrets_visible": False,
        "recommended_action": "Enter the exact founder approval phrase and execute only if the target revision is correct.",
    }


def execute_cloud_run_rollback(payload: dict[str, Any]) -> dict[str, Any]:
    request = _rollback_request(payload)
    errors: list[str] = []
    decision = authorize_governed_action(payload, "rollback", required_approval_phrase=APPROVAL_PHRASE, policy_context={"mission_state": True})
    if not decision.get("allowed"):
        errors.append(str(decision.get("reason") or "Governance authorization denied."))
    if payload.get("live_execution") is not True:
        errors.append("live_execution must be true.")
    if payload.get("approval_phrase") != APPROVAL_PHRASE:
        errors.append("approval_phrase must exactly match the required approval phrase.")
    if not request["target_revision"]:
        errors.append("target_revision is required.")
    if errors:
        return _blocked(request, " ".join(errors))

    state = _read_service_state(request)
    current = state["current_active_revision"]
    if request["target_revision"] == current:
        return _blocked(request, "target_revision is already the current active revision.", current)

    command = [
        "gcloud",
        "run",
        "services",
        "update-traffic",
        request["service_name"],
        "--region",
        request["region"],
        "--project",
        request["project_id"],
        "--to-revisions",
        f"{request['target_revision']}=100",
    ]
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        summary = _safe_text((result.stdout or "") + ("\n" + result.stderr if result.stderr else ""))
        status = "rollback-completed" if result.returncode == 0 else "rollback-failed"
        response = {
            "status": status,
            "service_name": request["service_name"],
            "region": request["region"],
            "project_id": request["project_id"],
            "previous_active_revision": current,
            "target_revision": request["target_revision"],
            "return_code": result.returncode,
            "traffic_result_summary": summary[-6000:],
            "traffic_shift_performed": result.returncode == 0,
            "deployment": False,
            "github_mutation": False,
            "pr_merge": False,
            "secrets_visible": False,
            "authorization": decision,
        }
        response["governance_evidence"] = record_governed_outcome(payload, decision, response)
        return response
    except OSError as exc:
        failed = _blocked(request, _safe_text(str(exc)), current)
        failed["status"] = "rollback-failed"
        return failed


def _rollback_request(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "service_name": _safe_slug(payload.get("service_name"), DEFAULT_SERVICE_NAME),
        "region": _safe_slug(payload.get("region"), DEFAULT_REGION),
        "project_id": _safe_slug(payload.get("project_id"), DEFAULT_PROJECT_ID),
        "target_revision": _safe_slug(payload.get("target_revision"), ""),
    }


def _safe_slug(value: Any, default: str) -> str:
    text = str(value or default).strip()
    if not text:
        return default
    return text if re.fullmatch(r"[A-Za-z0-9._-]{1,120}", text) else default


def _read_service_state(request: dict[str, str]) -> dict[str, Any]:
    errors: list[str] = []
    service = _run_json([
        "gcloud", "run", "services", "describe", request["service_name"],
        "--region", request["region"], "--project", request["project_id"],
        "--format", "json(status.traffic)",
    ], errors)
    revisions = _run_json([
        "gcloud", "run", "revisions", "list", "--service", request["service_name"],
        "--region", request["region"], "--project", request["project_id"],
        "--sort-by", "~metadata.creationTimestamp", "--limit", "10", "--format", "json",
    ], errors)
    traffic = ((service or {}).get("status") or {}).get("traffic") or []
    current = next((item.get("revisionName") for item in traffic if item.get("percent") == 100), None)
    recent = [_revision_name(item) for item in revisions if _revision_name(item)]
    return {"current_active_revision": current, "current_traffic": traffic, "recent_revisions": recent, "errors": errors}


def _run_json(command: list[str], errors: list[str]) -> Any:
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=False, timeout=25)
    except (OSError, subprocess.TimeoutExpired) as exc:
        errors.append(_safe_text(str(exc)))
        return None
    if result.returncode != 0:
        errors.append(_safe_text(result.stderr or result.stdout))
        return None
    try:
        return json.loads(result.stdout or "null")
    except json.JSONDecodeError:
        errors.append("gcloud returned invalid JSON.")
        return None


def _revision_name(item: dict[str, Any]) -> str | None:
    return str((item.get("metadata") or {}).get("name") or item.get("name") or "").strip() or None


def _recommended_revision(state: dict[str, Any]) -> str | None:
    current = state["current_active_revision"]
    return next((name for name in state["recent_revisions"] if name and name != current), None)


def _safe_text(value: str) -> str:
    redacted = value
    for key, secret in os.environ.items():
        if secret and any(word in key.upper() for word in ("TOKEN", "SECRET", "PASSWORD", "KEY")):
            redacted = redacted.replace(secret, "[redacted]")
    return redacted.replace("\n", " ").strip()[:6000]


def _blocked(request: dict[str, str], reason: str, current: str | None = None) -> dict[str, Any]:
    return {
        "status": "blocked",
        "service_name": request["service_name"],
        "region": request["region"],
        "project_id": request["project_id"],
        "previous_active_revision": current,
        "target_revision": request["target_revision"] or None,
        "recommended_action": reason,
        "traffic_shift_performed": False,
        "deployment": False,
        "github_mutation": False,
        "pr_merge": False,
        "secrets_visible": False,
    }
