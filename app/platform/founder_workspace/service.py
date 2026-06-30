from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from app.platform.founder_workspace.github_adapter import (
    GitHubRequestWriteAdapter,
    GitHubRequestWriteConfig,
    GitHubRequestWriteError,
)


def build_founder_workspace_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Founder Workspace",
        "purpose": "Founder-facing workspace for ideas, requests, proposals, approvals, and missions.",
        "status": "github-backed-request-write-adapter",
        "intake": {
            "endpoint": "/mission-control/requests",
            "method": "POST",
            "storage_target": "company/requests",
            "current_mode": "github-backed-write-adapter",
            "next_step": "GCP-03 Proposal Generator",
        },
    }


def build_request_intake(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_request_payload(payload)
    request_hash = _request_hash(normalized)
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    request_id = _request_id(created_at, request_hash)
    artifact_path = _artifact_path(created_at, request_id)
    artifact_content = _render_request_artifact(
        request_id=request_id,
        created_at=created_at,
        request_hash=request_hash,
        payload=normalized,
    )

    response: dict[str, Any] = {
        "company": "AI Software Factory",
        "product": "Founder Workspace",
        "status": "accepted",
        "request_id": request_id,
        "artifact_path": artifact_path,
        "title": normalized["title"],
        "description": normalized["description"],
        "created_at": created_at,
        "request_hash": request_hash,
        "next_step": "GCP-03 Proposal Generator",
    }

    config = GitHubRequestWriteConfig.from_environment()
    if config is None:
        response.update(
            {
                "status": "accepted-pending-github-configuration",
                "repository_write": {
                    "mode": "configuration-missing",
                    "required_environment": [
                        "GITHUB_TOKEN or GH_TOKEN",
                        "AI_FACTORY_REQUEST_REPOSITORY or GITHUB_REPOSITORY",
                    ],
                },
            }
        )
        return response

    try:
        write_result = GitHubRequestWriteAdapter(config).write_request_artifact(
            request_id=request_id,
            artifact_path=artifact_path,
            content=artifact_content,
            title=normalized["title"],
        )
    except GitHubRequestWriteError as exc:
        response.update(
            {
                "status": "accepted-github-write-failed",
                "repository_write": {
                    "mode": "github-error",
                    "error": str(exc),
                },
            }
        )
        return response

    response["repository_write"] = {
        "mode": write_result.mode,
        "repository": write_result.repository,
        "branch": write_result.branch,
        "path": write_result.path,
        "commit_sha": write_result.commit_sha,
        "pull_request_url": write_result.pull_request_url,
    }
    return response


def _normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("title") or "Untitled founder request").strip()
    description = str(payload.get("description") or payload.get("request") or "").strip()
    priority = str(payload.get("priority") or "normal").strip().lower()
    capability = str(payload.get("capability") or payload.get("area") or "general").strip()
    founder = str(payload.get("founder") or payload.get("actor") or "founder").strip()
    acceptance_criteria = payload.get("acceptance_criteria") or payload.get("acceptanceCriteria") or []
    labels = payload.get("labels") or []
    trace_id = str(payload.get("trace_id") or payload.get("traceId") or "").strip()

    if isinstance(acceptance_criteria, str):
        acceptance_criteria = [line.strip() for line in acceptance_criteria.splitlines() if line.strip()]
    if not isinstance(acceptance_criteria, list):
        acceptance_criteria = [str(acceptance_criteria)]

    if isinstance(labels, str):
        labels = [label.strip() for label in labels.split(",") if label.strip()]
    if not isinstance(labels, list):
        labels = [str(labels)]

    return {
        "title": title,
        "description": description,
        "priority": priority,
        "capability": capability,
        "founder": founder,
        "acceptance_criteria": [str(item).strip() for item in acceptance_criteria if str(item).strip()],
        "labels": [str(label).strip() for label in labels if str(label).strip()],
        "trace_id": trace_id,
    }


def _request_hash(payload: dict[str, Any]) -> str:
    stable_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(stable_payload.encode("utf-8")).hexdigest()


def _request_id(created_at: str, request_hash: str) -> str:
    date_prefix = created_at[:10].replace("-", "")
    return f"REQ-{date_prefix}-{request_hash[:12].upper()}"


def _artifact_path(created_at: str, request_id: str) -> str:
    year, month, _day = created_at[:10].split("-")
    return f"company/requests/{year}/{month}/{request_id}.md"


def _render_request_artifact(
    *,
    request_id: str,
    created_at: str,
    request_hash: str,
    payload: dict[str, Any],
) -> str:
    frontmatter = {
        "id": request_id,
        "type": "founder_request",
        "status": "accepted",
        "created_at": created_at,
        "request_hash": request_hash,
        "founder": payload["founder"],
        "priority": payload["priority"],
        "capability": payload["capability"],
        "trace_id": payload["trace_id"],
        "labels": payload["labels"],
    }

    acceptance = payload["acceptance_criteria"] or ["Proposal generated for founder review."]
    acceptance_markdown = "\n".join(f"- {item}" for item in acceptance)
    labels = ", ".join(payload["labels"]) if payload["labels"] else "none"

    return (
        "---\n"
        f"{_to_simple_yaml(frontmatter)}"
        "---\n\n"
        f"# {payload['title']}\n\n"
        "## Description\n\n"
        f"{payload['description'] or 'No description provided.'}\n\n"
        "## Acceptance Criteria\n\n"
        f"{acceptance_markdown}\n\n"
        "## Metadata\n\n"
        f"- Request ID: `{request_id}`\n"
        f"- Capability: `{payload['capability']}`\n"
        f"- Priority: `{payload['priority']}`\n"
        f"- Founder: `{payload['founder']}`\n"
        f"- Labels: {labels}\n"
        f"- Request Hash: `{request_hash}`\n"
        f"- Trace ID: `{payload['trace_id'] or 'none'}`\n"
    )


def _to_simple_yaml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            if value:
                lines.extend(f"  - {_yaml_scalar(item)}" for item in value)
            else:
                lines.append("  []")
        else:
            lines.append(f"{key}: {_yaml_scalar(value)}")
    return "\n".join(lines) + "\n"


def _yaml_scalar(value: Any) -> str:
    text = str(value)
    if not text:
        return '""'
    if re.fullmatch(r"[A-Za-z0-9_./:@+-]+", text):
        return text
    return json.dumps(text)
