from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
import shutil

from app.platform.execution.repository_adapter import repository_capability_probe
from app.platform.github_execution.adapter import github_capability_probe
from app.platform.governance_authorization.evidence import latest_execution_evidence
from app.platform.persistence.execution_migrations import execution_schema_status
from app.platform.release.execution_adapter import release_capability_probe


CAPABILITY_DOMAINS = {
    "repository": ("checkout", "fetch", "pull", "merge", "guarded_rebase", "guarded_reset", "cherry_pick", "revert"),
    "github": ("create_pr", "update_pr", "review_pr", "request_changes", "approve_pr", "merge_pr", "close_pr", "reopen_pr", "labels", "reviewers", "milestones", "workflow_inspection"),
    "release": ("create_release", "promote_release", "rollback_release", "compare_releases", "release_notes", "version_tags"),
    "deployment": ("deploy", "rollback", "verification"),
    "workspace": ("create_workspace", "resume_workspace", "lock_workspace", "recover_workspace", "cleanup_workspace", "destroy_workspace"),
}


def build_capability_matrix() -> List[Dict[str, Any]]:
    probes = {
        "repository": repository_capability_probe(), "github": github_capability_probe(),
        "release": release_capability_probe(), "workspace": execution_schema_status(),
        "deployment": _deployment_probe(),
    }
    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows = []
    for domain, capabilities in CAPABILITY_DOMAINS.items():
        probe = probes[domain]
        for capability in capabilities:
            evidence_key = _evidence_key(domain, capability)
            evidence = latest_execution_evidence(evidence_key)
            implemented = bool(probe.get("implemented"))
            configured = bool(probe.get("configured"))
            available = implemented and configured
            rows.append({
                "domain": domain, "capability": capability, "supported": implemented,
                "implemented": implemented, "configured": configured, "available": available,
                "mission_control": {"supported": implemented, "available": available},
                "codex": {"supported": implemented, "available": available},
                "authorized": "Authorized" if capability in {"checkout", "fetch", "workflow_inspection", "compare_releases", "release_notes", "verification"} else "Waiting Founder Approval",
                "evidence": evidence, "confidence": "high" if available else "medium",
                "freshness": evidence.get("observed_at") if evidence else checked_at,
                "unknown_reason": None if available else str(probe.get("detail") or "Runtime dependency is not configured."),
            })
    return rows


def _evidence_key(domain: str, capability: str) -> str:
    aliases = {("github", "create_pr"): "create_pr", ("github", "merge_pr"): "merge_pr", ("deployment", "deploy"): "deploy", ("deployment", "rollback"): "rollback", ("deployment", "verification"): "production_verification"}
    return aliases.get((domain, capability), "%s_%s" % (domain, capability))


def _deployment_probe() -> Dict[str, Any]:
    try:
        from app.platform.deployment.approved_cloud_run import build_cloud_run_deployment_summary
        summary = build_cloud_run_deployment_summary()
        executable = shutil.which("gcloud")
        return {"implemented": True, "configured": bool(executable), "detail": summary.get("status") if executable else "gcloud executable is unavailable"}
    except Exception as exc:
        return {"implemented": True, "configured": False, "detail": type(exc).__name__}
