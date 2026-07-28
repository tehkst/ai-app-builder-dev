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
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
DEPLOY_WORKFLOW_FILE = "platform-deploy.yml"

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


def trigger_production_deploy(payload: dict[str, Any]) -> dict[str, Any]:
    """Kick off a real production deploy via the platform-deploy.yml GitHub Actions workflow
    - the same one every other deploy this session has used - instead of running gcloud as a
    subprocess inside this container's own request handler.

    execute_cloud_run_deployment (above) does the gcloud call in-process, which blocks the
    HTTP request for as long as the deploy takes (60-120+ seconds). Cloud Run only reliably
    grants CPU while a request is being served, so a deploy that outlives the request risks
    silent starvation on top of the more visible risk of the request itself timing out (both
    observed in practice: a live invocation returned an honest 504 upstream timeout, with no
    way to tell whether the deploy underneath had actually completed). Dispatching to GitHub
    Actions runs the actual work on infrastructure with no such constraint; this function only
    has to validate governance and fire the dispatch, both fast.
    """
    decision = authorize_governed_action(payload, "deploy", required_approval_phrase=APPROVAL_PHRASE, policy_context={"mission_state": True, "release_gates": bool(payload.get("release_gates_passed", True))})
    errors: list[str] = []
    if not decision.get("allowed"):
        errors.append(str(decision.get("reason") or "Governance authorization denied."))
    if payload.get("live_execution") is not True:
        errors.append("live_execution must be true.")
    if payload.get("approval_phrase") != APPROVAL_PHRASE:
        errors.append("approval_phrase must exactly match the required approval phrase.")
    if errors:
        return {"status": "blocked", "recommended_action": " ".join(errors)}

    token = os.getenv(GITHUB_TOKEN_ENV)
    if not token:
        return {"status": "blocked", "recommended_action": "GITHUB_TOKEN is not mounted."}

    from app.platform.github_execution.approved_merge import REPOSITORY_FULL_NAME, _github_get

    try:
        head = _github_get("/commits/main", token)
        head_sha = str(head.get("sha") or "")
        _dispatch_deploy_workflow(token)
    except RuntimeError as exc:
        return {"status": "blocked", "recommended_action": "Could not trigger the deploy workflow: %s" % exc}

    response = {
        "status": "deploy-triggered",
        "repository": REPOSITORY_FULL_NAME,
        "expected_head_sha": head_sha,
        "workflow": DEPLOY_WORKFLOW_FILE,
        "authorization": decision,
    }
    response["governance_evidence"] = record_governed_outcome(payload, decision, response)
    return response


def check_production_deploy_status(payload: dict[str, Any]) -> dict[str, Any]:
    auth = require_founder(payload)
    if not auth.get("authorized"):
        return {"status": "blocked", "recommended_action": "Founder token is invalid or missing."}
    token = os.getenv(GITHUB_TOKEN_ENV)
    if not token:
        return {"status": "blocked", "recommended_action": "GITHUB_TOKEN is not mounted."}
    expected_head_sha = str(payload.get("expected_head_sha") or "")

    from app.platform.github_execution.approved_merge import _github_get

    try:
        runs = _github_get(
            "/actions/workflows/%s/runs" % DEPLOY_WORKFLOW_FILE,
            token,
            params={"branch": "main", "event": "workflow_dispatch", "per_page": 10},
        )
    except RuntimeError as exc:
        return {"status": "polling_error", "error": str(exc)}

    run = None
    for candidate in runs.get("workflow_runs") or []:
        if expected_head_sha and candidate.get("head_sha") == expected_head_sha:
            run = candidate
            break
    if run is None:
        return {"status": "queued", "current_step": "Waiting for GitHub Actions to pick up the deploy"}

    if run.get("status") != "completed":
        current_step = _current_job_step(int(run["id"]), token)
        return {
            "status": "in_progress",
            "current_step": current_step or ("Running: %s" % (run.get("status") or "workflow")),
            "run_url": run.get("html_url"),
        }

    conclusion = run.get("conclusion")
    return {
        "status": "completed",
        "conclusion": conclusion,
        "run_url": run.get("html_url"),
        "summary": "Deploy workflow finished with conclusion: %s" % conclusion,
    }


def _dispatch_deploy_workflow(token: str) -> None:
    import requests

    from app.platform.github_execution.approved_merge import GITHUB_API_BASE, REPOSITORY_FULL_NAME

    try:
        response = requests.post(
            "%s/repos/%s/actions/workflows/%s/dispatches" % (GITHUB_API_BASE, REPOSITORY_FULL_NAME, DEPLOY_WORKFLOW_FILE),
            json={
                "ref": "main",
                "inputs": {"environment": "production", "publish_image": "true", "deploy_service": "true"},
            },
            timeout=30,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer %s" % token,
                "User-Agent": "mission-control-approved-deploy",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
    except requests.RequestException as exc:
        raise RuntimeError("GitHub request failed.") from exc
    # workflow_dispatch returns 204 No Content on success - no JSON body to parse.
    if response.status_code >= 400:
        raise RuntimeError("GitHub request failed: HTTP %d" % response.status_code)


def _current_job_step(run_id: int, token: str) -> str | None:
    from app.platform.github_execution.approved_merge import _github_get

    try:
        jobs = _github_get("/actions/runs/%d/jobs" % run_id, token)
    except RuntimeError:
        return None
    for job in jobs.get("jobs") or []:
        if job.get("status") == "completed":
            continue
        for step in job.get("steps") or []:
            if step.get("status") in {"in_progress", "queued"}:
                return "%s: %s" % (job.get("name"), step.get("name"))
        return job.get("name")
    return None


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
