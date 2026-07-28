from __future__ import annotations

from typing import Any, Dict, List


VALIDATION_CATALOGUE = {
    "repository": (
        "repository_checkout", "repository_fetch", "repository_pull", "repository_merge",
        "repository_rebase", "repository_reset", "repository_cherry_pick", "repository_revert",
    ),
    "github": (
        "create_pr", "github_update_pr", "github_review_pr", "github_request_changes",
        "github_approve_pr", "merge_pr", "github_close_pr", "github_reopen_pr",
        "github_labels", "github_assign_reviewers", "github_workflow_inspection",
    ),
    "release": (
        "release_create_release", "release_release_notes", "release_version_tag",
        "release_promote_release", "release_rollback_release", "release_compare_releases",
    ),
    "workspace": (
        "workspace_create", "workspace_lock", "workspace_heartbeat", "workspace_isolation",
        "workspace_recover", "workspace_cleanup", "workspace_retention",
    ),
    "founder_approval": (
        "approval_request", "approval_grant", "approval_consume", "approval_replay_denial",
        "approval_expiry", "approval_scope_enforcement",
    ),
    "governance": (
        "governance_unauthorized_denial", "governance_authorized_execution",
        "governance_central_authority_evidence",
    ),
    "deployment": (
        "deploy", "production_verification", "deployment_readiness", "rollback_readiness",
    ),
    "end_to_end": (
        "founder_request", "approval_grant", "workspace_create", "repository_checkout",
        "create_pr", "merge_pr", "release_create_release", "deploy",
        "production_verification", "mission_completion",
    ),
    "digital_twin": (
        "sandbox_tool_execution", "ui_ux_verification",
    ),
}


def validation_catalogue() -> List[Dict[str, Any]]:
    return [
        {"validation_type": name, "capabilities": list(capabilities), "repeatable": True}
        for name, capabilities in VALIDATION_CATALOGUE.items()
    ]


def capabilities_for(validation_type: str) -> List[str]:
    return list(VALIDATION_CATALOGUE.get(validation_type, ()))
