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


def build_proposal_generator_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Proposal Generator",
        "milestone": "GCP-03",
        "status": "proposal-generator-ready",
        "endpoint": "/mission-control/proposals/generate",
        "method": "POST",
        "storage_target": "company/proposals",
        "next_step": "GCP-04 Founder Approval Workflow",
    }


def generate_proposal(payload: dict[str, Any]) -> dict[str, Any]:
    request = _normalize_request(payload)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    proposal_hash = _stable_hash(request)
    proposal_id = _proposal_id(generated_at, proposal_hash)
    artifact_path = _artifact_path(generated_at, proposal_id)
    proposal = _build_structured_proposal(
        proposal_id=proposal_id,
        generated_at=generated_at,
        proposal_hash=proposal_hash,
        request=request,
    )
    artifact_content = _render_proposal_markdown(proposal)

    response: dict[str, Any] = {
        "company": "AI Software Factory",
        "product": "Proposal Generator",
        "status": "generated",
        "proposal_id": proposal_id,
        "request_id": request["request_id"],
        "artifact_path": artifact_path,
        "proposal_hash": proposal_hash,
        "proposal": proposal,
        "next_step": "GCP-04 Founder Approval Workflow",
    }

    config = GitHubRequestWriteConfig.from_environment()
    if config is None:
        response.update(
            {
                "status": "generated-pending-github-configuration",
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
            request_id=proposal_id,
            artifact_path=artifact_path,
            content=artifact_content,
            title=proposal["title"],
        )
    except GitHubRequestWriteError as exc:
        response.update(
            {
                "status": "generated-github-write-failed",
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


def _normalize_request(payload: dict[str, Any]) -> dict[str, Any]:
    request_payload = payload.get("request") if isinstance(payload.get("request"), dict) else payload
    request_id = str(request_payload.get("request_id") or request_payload.get("id") or "REQ-UNSPECIFIED").strip()
    title = str(request_payload.get("title") or "Untitled founder request").strip()
    description = str(request_payload.get("description") or request_payload.get("request") or "").strip()
    capability = str(request_payload.get("capability") or request_payload.get("area") or "Mission Control").strip()
    priority = str(request_payload.get("priority") or "normal").strip().lower()
    acceptance_criteria = request_payload.get("acceptance_criteria") or request_payload.get("acceptanceCriteria") or []
    labels = request_payload.get("labels") or []

    if isinstance(acceptance_criteria, str):
        acceptance_criteria = [line.strip() for line in acceptance_criteria.splitlines() if line.strip()]
    if not isinstance(acceptance_criteria, list):
        acceptance_criteria = [str(acceptance_criteria)]

    if isinstance(labels, str):
        labels = [label.strip() for label in labels.split(",") if label.strip()]
    if not isinstance(labels, list):
        labels = [str(labels)]

    return {
        "request_id": request_id,
        "title": title,
        "description": description,
        "capability": capability,
        "priority": priority,
        "acceptance_criteria": [str(item).strip() for item in acceptance_criteria if str(item).strip()],
        "labels": [str(label).strip() for label in labels if str(label).strip()],
    }


def _stable_hash(data: dict[str, Any]) -> str:
    stable_payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(stable_payload.encode("utf-8")).hexdigest()


def _proposal_id(generated_at: str, proposal_hash: str) -> str:
    date_prefix = generated_at[:10].replace("-", "")
    return f"PROP-{date_prefix}-{proposal_hash[:12].upper()}"


def _artifact_path(generated_at: str, proposal_id: str) -> str:
    year, month, _day = generated_at[:10].split("-")
    return f"company/proposals/{year}/{month}/{proposal_id}.md"


def _build_structured_proposal(
    *,
    proposal_id: str,
    generated_at: str,
    proposal_hash: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    acceptance = request["acceptance_criteria"] or [
        "Proposal is generated and available for founder review.",
        "No mission execution begins before founder approval.",
    ]
    return {
        "proposal_id": proposal_id,
        "request_id": request["request_id"],
        "title": f"Proposal for {request['title']}",
        "status": "generated",
        "generated_at": generated_at,
        "proposal_hash": proposal_hash,
        "executive_summary": (
            f"Generate a founder-reviewable implementation proposal for `{request['title']}` "
            "before any engineering execution begins."
        ),
        "business_objective": request["description"] or "Clarify the founder request into an executable engineering plan.",
        "recommended_solution": (
            "Create a structured proposal object and human-readable Markdown artifact that can feed "
            "GCP-04 approval and GCP-05 mission execution."
        ),
        "architecture_impact": {
            "components": ["Founder Workspace", "Mission Control", "Company Brain repository artifacts"],
            "apis": ["POST /mission-control/proposals/generate"],
            "repositories": ["company/proposals"],
            "files_expected_to_change": [
                "app/platform/proposal_generator/service.py",
                "app/platform/server.py",
                "app/platform/api_contract.py",
            ],
        },
        "database_impact": "None for GCP-03. Proposal state is repository-backed.",
        "api_changes": [
            {
                "method": "POST",
                "path": "/mission-control/proposals/generate",
                "purpose": "Generate a repository-backed engineering proposal from a founder request.",
            }
        ],
        "risk_assessment": [
            "Generated proposal quality depends on request clarity.",
            "Repository write requires GitHub credentials in production.",
            "Approval workflow is intentionally deferred to GCP-04.",
        ],
        "dependencies": ["GCP-02 GitHub-backed Request Write Adapter", "CI-01 PR Validation Pipeline"],
        "estimated_complexity": _estimate_complexity(request),
        "estimated_duration": "0.5-1 engineering day for baseline capability; longer for AI-assisted planning.",
        "acceptance_criteria": acceptance,
        "rollback_plan": "Disable or remove the proposal endpoint and leave existing request intake unchanged.",
    }


def _estimate_complexity(request: dict[str, Any]) -> str:
    text = f"{request['title']} {request['description']}".lower()
    if any(word in text for word in ["database", "auth", "payment", "deploy", "migration", "security"]):
        return "medium"
    return "low"


def _render_proposal_markdown(proposal: dict[str, Any]) -> str:
    frontmatter = {
        "id": proposal["proposal_id"],
        "type": "engineering_proposal",
        "status": proposal["status"],
        "request_id": proposal["request_id"],
        "generated_at": proposal["generated_at"],
        "proposal_hash": proposal["proposal_hash"],
        "next_step": "GCP-04 Founder Approval Workflow",
    }
    architecture = proposal["architecture_impact"]
    api_changes = "\n".join(f"- `{item['method']} {item['path']}` — {item['purpose']}" for item in proposal["api_changes"])
    risks = "\n".join(f"- {risk}" for risk in proposal["risk_assessment"])
    dependencies = "\n".join(f"- {item}" for item in proposal["dependencies"])
    acceptance = "\n".join(f"- {item}" for item in proposal["acceptance_criteria"])
    files = "\n".join(f"- `{item}`" for item in architecture["files_expected_to_change"])

    return (
        "---\n"
        f"{_to_simple_yaml(frontmatter)}"
        "---\n\n"
        f"# {proposal['title']}\n\n"
        "## Executive Summary\n\n"
        f"{proposal['executive_summary']}\n\n"
        "## Business Objective\n\n"
        f"{proposal['business_objective']}\n\n"
        "## Recommended Solution\n\n"
        f"{proposal['recommended_solution']}\n\n"
        "## Architecture Impact\n\n"
        f"- Components: {', '.join(architecture['components'])}\n"
        f"- Repositories: {', '.join(architecture['repositories'])}\n\n"
        "## Files Expected to Change\n\n"
        f"{files}\n\n"
        "## Database Impact\n\n"
        f"{proposal['database_impact']}\n\n"
        "## API Changes\n\n"
        f"{api_changes}\n\n"
        "## Risk Assessment\n\n"
        f"{risks}\n\n"
        "## Dependencies\n\n"
        f"{dependencies}\n\n"
        "## Estimated Complexity\n\n"
        f"{proposal['estimated_complexity']}\n\n"
        "## Estimated Duration\n\n"
        f"{proposal['estimated_duration']}\n\n"
        "## Acceptance Criteria\n\n"
        f"{acceptance}\n\n"
        "## Rollback Plan\n\n"
        f"{proposal['rollback_plan']}\n"
    )


def _to_simple_yaml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in data.items():
        lines.append(f"{key}: {_yaml_scalar(value)}")
    return "\n".join(lines) + "\n"


def _yaml_scalar(value: Any) -> str:
    text = str(value)
    if not text:
        return '""'
    if re.fullmatch(r"[A-Za-z0-9_./:@+-]+", text):
        return text
    return json.dumps(text)
