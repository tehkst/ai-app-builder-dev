from __future__ import annotations

import re
from typing import Any, Callable, Dict, List


def authority_entries(source: Dict[str, Any], entry: Callable[..., Dict[str, Any]]) -> List[Dict[str, Any]]:
    values = []
    for item in source["approvals"]:
        status = "revoked" if item.get("revoked_at") else "authorized"
        values.append(entry(
            source, "authorization_%s" % status, "governance", status,
            "Founder authorization recorded for %s." % item["action"],
            "PlatformGovernanceApproval", item["approval_id"], item.get("approved_at"),
            actor=item.get("approved_by"), approval_refs=[item["approval_id"]],
            governance_boundary=item.get("scope"),
        ))
    for item in source["execution_evidence"]:
        refs = [str(value) for value in item.get("artifacts", {}).values() if value]
        event_type = _capability_event(item["capability"])
        values.append(entry(
            source, event_type, _capability_stage(item["capability"]),
            item["outcome"], "Governed %s finished with status %s." % (item["requested_action"], item["outcome"]),
            "PlatformExecutionEvidence", item["evidence_id"], item.get("created_at"),
            actor=item.get("actor"),
            repository_refs=refs if event_type in {"repository_execution", "merged"} else [],
            deployment_refs=_execution_deployment_refs(item.get("artifacts") or {}) if event_type == "deployment_succeeded" else [],
            evidence_refs=[item["evidence_id"]],
            governance_boundary=str(item.get("authorization", {}).get("governing_policy") or "governance-authorization"),
        ))
    for item in source["operational_evidence"]:
        values.append(entry(
            source, item["evidence_type"], _capability_stage(item["evidence_type"]), item["status"],
            "%s observed by %s." % (item["evidence_type"].replace("_", " ").title(), item["authority"]),
            "PlatformOperationalEvidence", item["evidence_id"], item.get("observed_at"),
            evidence_refs=[item["evidence_id"]], deployment_refs=_deployment_refs(item),
        ))
    return values


def _capability_event(value: str) -> str:
    text = str(value).lower()
    if "merge" in text:
        return "merged"
    if "deploy" in text:
        return "deployment_succeeded"
    if "github" in text or "repository" in text:
        return "repository_execution"
    return "governed_action"


def _capability_stage(value: str) -> str:
    text = str(value).lower()
    if "verification" in text:
        return "production_verification"
    if "deploy" in text or "release" in text:
        return "deployment"
    if "merge" in text:
        return "merge"
    if "github" in text or "repository" in text or "pull" in text:
        return "repository"
    return "governance"


def _deployment_refs(item: Dict[str, Any]) -> List[str]:
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
    return [str(payload[key]) for key in ("revision_name", "deployment_revision", "service") if payload.get(key)]


def _execution_deployment_refs(artifacts: Dict[str, Any]) -> List[str]:
    values = [
        str(artifacts.get(key) or "")
        for key in ("revision_name", "target_revision", "release_url")
    ]
    return [
        value for value in values
        if value.startswith("https://") or re.fullmatch(r"[a-z0-9-]+-\d{5}-[a-z0-9]{3}", value)
    ]
