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


def build_founder_approval_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Founder Approval Workflow",
        "milestone": "GCP-04",
        "status": "founder-approval-ready",
        "governance_rule": "No mission execution begins without explicit founder approval.",
        "endpoints": {
            "proposal_status": "GET /mission-control/proposals/{proposal_id}",
            "approve": "POST /mission-control/proposals/approve",
            "reject": "POST /mission-control/proposals/reject",
        },
        "storage_targets": ["company/approvals", "company/missions"],
        "next_step": "GCP-05 Mission Execution Bridge",
    }


def get_proposal_status(proposal_id: str) -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Founder Approval Workflow",
        "proposal_id": proposal_id,
        "status": "pending-founder-approval",
        "allowed_actions": ["approve", "reject"],
        "governance_rule": "Proposal must be approved before a mission can be created.",
        "next_step": "Approve or reject proposal.",
    }


def approve_proposal(payload: dict[str, Any]) -> dict[str, Any]:
    decision_at = _now()
    proposal_id = _required_text(payload, "proposal_id", "PROP-UNSPECIFIED")
    request_id = _text(payload, "request_id", "REQ-UNSPECIFIED")
    approved_by = _text(payload, "approved_by", _text(payload, "actor", "Founder"))
    comment = _text(payload, "comment", "Approved for mission creation.")
    approval_id = _id("APPR", decision_at, {"proposal_id": proposal_id, "decision": "approved", "approved_by": approved_by})
    supplied_mission_id = _text(payload, "mission_id", "")
    mission_id = supplied_mission_id if _is_canonical_mission_id(supplied_mission_id) else _id("MISSION", decision_at, {"proposal_id": proposal_id, "approval_id": approval_id})
    originating_mission_id = _text(payload, "originating_mission_id", "") or (supplied_mission_id if supplied_mission_id != mission_id else "")

    approval_record = {
        "approval_id": approval_id,
        "proposal_id": proposal_id,
        "request_id": request_id,
        "decision": "approved",
        "approved_by": approved_by,
        "timestamp": decision_at,
        "comment": comment,
        "mission_id": mission_id,
        "originating_mission_id": originating_mission_id or None,
        "status": "mission-created",
    }
    mission_record = {
        "mission_id": mission_id,
        "originating_mission_id": originating_mission_id or None,
        "proposal_id": proposal_id,
        "request_id": request_id,
        "approval_id": approval_id,
        "status": "created",
        "created_at": decision_at,
        "created_by": "Founder Approval Workflow",
        "acceptance_criteria": _list(payload.get("acceptance_criteria") or payload.get("acceptanceCriteria")),
        "execution_state": "awaiting-gcp-05-execution-bridge",
        "rollback_reference": "Return mission to approved proposal state and halt execution.",
    }

    approval_path = _artifact_path("approvals", decision_at, approval_id, "json")
    mission_path = _artifact_path("missions", decision_at, mission_id, "md")

    response: dict[str, Any] = {
        "company": "AI Software Factory",
        "product": "Founder Approval Workflow",
        "status": "approved",
        "approval_id": approval_id,
        "proposal_id": proposal_id,
        "request_id": request_id,
        "mission_id": mission_id,
        "originating_mission_id": originating_mission_id or None,
        "approval_artifact_path": approval_path,
        "mission_artifact_path": mission_path,
        "approval": approval_record,
        "mission": mission_record,
        "next_step": "GCP-05 Mission Execution Bridge",
    }

    if payload.get("persist_repository_artifacts") is False:
        writes = {"mode": "disabled-by-governance", "artifacts": []}
    else:
        writes = _write_artifacts(
            [
                (approval_id, approval_path, json.dumps(approval_record, indent=2, sort_keys=True) + "\n", f"Approve proposal {proposal_id}"),
                (mission_id, mission_path, _render_mission_markdown(mission_record), f"Create mission {mission_id}"),
            ]
        )
    response["repository_write"] = writes
    if writes["mode"] == "configuration-missing":
        response["status"] = "approved-pending-github-configuration"
    elif writes["mode"] == "github-error":
        response["status"] = "approved-github-write-failed"
    return response


def reject_proposal(payload: dict[str, Any]) -> dict[str, Any]:
    decision_at = _now()
    proposal_id = _required_text(payload, "proposal_id", "PROP-UNSPECIFIED")
    request_id = _text(payload, "request_id", "REQ-UNSPECIFIED")
    rejected_by = _text(payload, "rejected_by", _text(payload, "actor", "Founder"))
    reason = _text(payload, "reason", "Rejected for revision.")
    approval_id = _id("APPR", decision_at, {"proposal_id": proposal_id, "decision": "rejected", "rejected_by": rejected_by})

    rejection_record = {
        "approval_id": approval_id,
        "proposal_id": proposal_id,
        "request_id": request_id,
        "decision": "rejected",
        "rejected_by": rejected_by,
        "timestamp": decision_at,
        "reason": reason,
        "status": "needs-revision",
        "mission_id": None,
    }
    rejection_path = _artifact_path("approvals", decision_at, approval_id, "json")

    response: dict[str, Any] = {
        "company": "AI Software Factory",
        "product": "Founder Approval Workflow",
        "status": "rejected",
        "approval_id": approval_id,
        "proposal_id": proposal_id,
        "request_id": request_id,
        "approval_artifact_path": rejection_path,
        "approval": rejection_record,
        "next_step": "Proposal Revision",
    }

    if payload.get("persist_repository_artifacts") is False:
        writes = {"mode": "disabled-by-governance", "artifacts": []}
    else:
        writes = _write_artifacts(
            [(approval_id, rejection_path, json.dumps(rejection_record, indent=2, sort_keys=True) + "\n", f"Reject proposal {proposal_id}")]
        )
    response["repository_write"] = writes
    if writes["mode"] == "configuration-missing":
        response["status"] = "rejected-pending-github-configuration"
    elif writes["mode"] == "github-error":
        response["status"] = "rejected-github-write-failed"
    return response


def _write_artifacts(artifacts: list[tuple[str, str, str, str]]) -> dict[str, Any]:
    config = GitHubRequestWriteConfig.from_environment()
    if config is None:
        return {
            "mode": "configuration-missing",
            "required_environment": [
                "GITHUB_TOKEN or GH_TOKEN",
                "AI_FACTORY_REQUEST_REPOSITORY or GITHUB_REPOSITORY",
            ],
        }

    results: list[dict[str, Any]] = []
    try:
        adapter = GitHubRequestWriteAdapter(config)
        for artifact_id, path, content, title in artifacts:
            result = adapter.write_request_artifact(
                request_id=artifact_id,
                artifact_path=path,
                content=content,
                title=title,
            )
            results.append(
                {
                    "artifact_id": artifact_id,
                    "mode": result.mode,
                    "repository": result.repository,
                    "branch": result.branch,
                    "path": result.path,
                    "commit_sha": result.commit_sha,
                    "pull_request_url": result.pull_request_url,
                }
            )
    except GitHubRequestWriteError as exc:
        return {"mode": "github-error", "error": str(exc), "artifacts": results}

    return {"mode": "github", "artifacts": results}


def _render_mission_markdown(mission: dict[str, Any]) -> str:
    criteria = mission["acceptance_criteria"] or ["Mission is ready for GCP-05 execution planning."]
    criteria_md = "\n".join(f"- {item}" for item in criteria)
    return (
        "---\n"
        f"id: {mission['mission_id']}\n"
        "type: mission\n"
        f"status: {mission['status']}\n"
        f"proposal_id: {mission['proposal_id']}\n"
        f"request_id: {mission['request_id']}\n"
        f"approval_id: {mission['approval_id']}\n"
        f"originating_mission_id: {_yaml_scalar(mission.get('originating_mission_id') or '')}\n"
        f"created_at: {mission['created_at']}\n"
        "---\n\n"
        f"# Mission {mission['mission_id']}\n\n"
        "## Linked Artifacts\n\n"
        f"- Request: `{mission['request_id']}`\n"
        f"- Proposal: `{mission['proposal_id']}`\n"
        f"- Approval: `{mission['approval_id']}`\n\n"
        "## Acceptance Criteria\n\n"
        f"{criteria_md}\n\n"
        "## Execution State\n\n"
        f"{mission['execution_state']}\n\n"
        "## Rollback Reference\n\n"
        f"{mission['rollback_reference']}\n"
    )


def _artifact_path(kind: str, timestamp: str, artifact_id: str, extension: str) -> str:
    year, month, _day = timestamp[:10].split("-")
    return f"company/{kind}/{year}/{month}/{artifact_id}.{extension}"


def _id(prefix: str, timestamp: str, data: dict[str, Any]) -> str:
    date_prefix = timestamp[:10].replace("-", "")
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}-{date_prefix}-{digest}"


def _is_canonical_mission_id(value: str) -> bool:
    return bool(re.fullmatch(r"MISSION-[A-Za-z0-9][A-Za-z0-9-]*", value))


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _required_text(payload: dict[str, Any], key: str, default: str) -> str:
    return _text(payload, key, default)


def _text(payload: dict[str, Any], key: str, default: str) -> str:
    value = str(payload.get(key) or default).strip()
    return value or default


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _yaml_scalar(value: Any) -> str:
    text = str(value)
    if not text:
        return '""'
    if re.fullmatch(r"[A-Za-z0-9_./:@+-]+", text):
        return text
    return json.dumps(text)
