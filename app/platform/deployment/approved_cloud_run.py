from __future__ import annotations

import os
import re
import subprocess
from typing import Any

from app.platform.auth.service import require_founder
from app.platform.governance_authorization.service import authorize_governed_action, record_governed_outcome

APPROVAL_PHRASE = "I APPROVE CLOUD RUN DEPLOYMENT"
DEFAULT_PROJECT_ID = "ai-software-factory-500910"
DEFAULT_REGION = "asia-southeast1"
DEFAULT_SERVICE_NAME = "ai-software-factory-production"
DEFAULT_SOURCE_REF = "main"

def build_cloud_run_deployment_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Founder-approved Cloud Run Deployment",
        "status": "configured",
        "service_name": DEFAULT_SERVICE_NAME,
        "region": DEFAULT_REGION,
        "project_id": DEFAULT_PROJECT_ID,
        "source_ref": DEFAULT_SOURCE_REF,
        "required_approval_phrase": APPROVAL_PHRASE,
        "governance": {
            "founder_token_required": True,
            "live_execution_required": True,
            "approval_phrase_required": True,
            "traffic_shift_endpoint": False,
            "rollback": False,
            "github_mutation": False,
            "pr_merge": False,
            "secrets_exposed": False,
        },
        "endpoints": {
            "summary": "GET /mission-control/deployment",
            "preview": "POST /mission-control/deployment/preview",
            "execute": "POST /mission-control/deployment/execute",
        },
    }

def preview_cloud_run_deployment(payload: dict[str, Any]) -> dict[str, Any]:
    auth = require_founder(payload)
    request = _deployment_request(payload)
    if not auth.get("authorized"):
        return _blocked(request, "Founder token is invalid or missing.")
    traffic = _current_traffic(request)
    return {
        "status": "deployment-preview-ready",
        "service_name": request["service_name"],
        "region": request["region"],
        "project_id": request["project_id"],
        "source_ref": request["source_ref"],
        "source_directory": request["source_directory"],
        "current_traffic": traffic,
        "deploy_command": _redacted_command(request),
        "deployment_performed": False,
        "traffic_shift": False,
        "rollback": False,
        "github_mutation": False,
        "pr_merge": False,
        "secrets_visible": False,
        "recommended_action": "Review target and enter the exact founder approval phrase before live deployment.",
    }

def execute_cloud_run_deployment(payload: dict[str, Any]) -> dict[str, Any]:
    request = _deployment_request(payload)
    errors: list[str] = []
    decision = authorize_governed_action(payload, "deploy", required_approval_phrase=APPROVAL_PHRASE, policy_context={"mission_state": True, "release_gates": bool(payload.get("release_gates_passed", True))})
    if not decision.get("allowed"):
        errors.append(str(decision.get("reason") or "Governance authorization denied."))
    if payload.get("live_execution") is not True:
        errors.append("live_execution must be true.")
    if payload.get("approval_phrase") != APPROVAL_PHRASE:
        errors.append("approval_phrase must exactly match the required approval phrase.")
    if request["source_ref"] != DEFAULT_SOURCE_REF:
        errors.append("source_ref must be main for this deployment gate.")
    if errors:
        return _blocked(request, " ".join(errors))

    command = _deploy_command(request)
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=False)
    except OSError as exc:
        return {
            "status": "deployment-failed",
            "service_name": request["service_name"],
            "region": request["region"],
            "project_id": request["project_id"],
            "source_ref": request["source_ref"],
            "revision_name": None,
            "service_url": None,
            "summary": _safe_text(str(exc)),
            "deployment_performed": False,
            "traffic_shift": False,
            "rollback": False,
            "github_mutation": False,
            "pr_merge": False,
            "secrets_visible": False,
        }
    output = _safe_text((result.stdout or "") + ("\n" + result.stderr if result.stderr else ""))
    revision = _extract_revision(output)
    service_url = _extract_service_url(output)
    status = "deployment-completed" if result.returncode == 0 else "deployment-failed"
    response = {
        "status": status,
        "service_name": request["service_name"],
        "region": request["region"],
        "project_id": request["project_id"],
        "source_ref": request["source_ref"],
        "source_directory": request["source_directory"],
        "revision_name": revision,
        "service_url": service_url,
        "return_code": result.returncode,
        "summary": output[-6000:],
        "deployment_performed": result.returncode == 0,
        "traffic_shift": False,
        "rollback": False,
        "github_mutation": False,
        "pr_merge": False,
        "secrets_visible": False,
        "authorization": decision,
    }
    response["governance_evidence"] = record_governed_outcome(payload, decision, response)
    if response["status"] == "deployment-completed":
        from app.platform.operating_console.delivery_link import link_authority_result

        return link_authority_result(
            payload,
            response,
            authority="cloud_run_deployment",
            event_key=revision or service_url,
        )
    return response

def _deployment_request(payload: dict[str, Any]) -> dict[str, str]:
    from app.platform.saas_builder.deployment import bounded_source_directory

    return {
        "service_name": _safe_slug(payload.get("service_name"), DEFAULT_SERVICE_NAME),
        "region": _safe_slug(payload.get("region"), DEFAULT_REGION),
        "project_id": _safe_slug(payload.get("project_id"), DEFAULT_PROJECT_ID),
        "source_ref": _safe_slug(payload.get("source_ref"), DEFAULT_SOURCE_REF),
        "source_directory": bounded_source_directory(payload.get("source_directory")),
    }

def _safe_slug(value: Any, default: str) -> str:
    text = str(value or default).strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", text):
        return default
    return text

def _current_traffic(request: dict[str, str]) -> dict[str, Any]:
    command = [
        "gcloud",
        "run",
        "services",
        "describe",
        request["service_name"],
        "--region",
        request["region"],
        "--project",
        request["project_id"],
        "--format",
        "json(status.traffic,status.url)",
    ]
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=False, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": _safe_text(str(exc))}
    if result.returncode != 0:
        return {"available": False, "error": _safe_text(result.stderr or result.stdout)}
    return {"available": True, "raw": _safe_text(result.stdout)}

def _deploy_command(request: dict[str, str]) -> list[str]:
    from app.platform.saas_builder.deployment import deployment_options

    public_access_flag = (
        "--no-invoker-iam-check"
        if request["source_directory"] != "."
        else "--allow-unauthenticated"
    )
    return [
        "gcloud",
        "run",
        "deploy",
        request["service_name"],
        "--source",
        request["source_directory"],
        "--region",
        request["region"],
        "--project",
        request["project_id"],
        public_access_flag,
    ] + deployment_options(request)

def _redacted_command(request: dict[str, str]) -> list[str]:
    return list(_deploy_command(request))


def _extract_revision(output: str) -> str | None:
    match = re.search(r"Revision\s+\[([^\]]+)\]", output, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"\b(ai-software-factory-production-[a-z0-9-]+)\b", output)
    return match.group(1) if match else None


def _extract_service_url(output: str) -> str | None:
    match = re.search(r"https://[^\s]+", output)
    return match.group(0) if match else None


def _safe_text(value: str) -> str:
    redacted = value
    for key, secret in os.environ.items():
        if any(word in key.upper() for word in ("TOKEN", "SECRET", "PASSWORD", "KEY")) and secret:
            redacted = redacted.replace(secret, "[redacted]")
    return redacted.strip()


def _blocked(request: dict[str, str], reason: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "service_name": request["service_name"],
        "region": request["region"],
        "project_id": request["project_id"],
        "source_ref": request["source_ref"],
        "source_directory": request["source_directory"],
        "recommended_action": reason,
        "deployment_performed": False,
        "traffic_shift": False,
        "rollback": False,
        "github_mutation": False,
        "pr_merge": False,
        "secrets_visible": False,
    }
