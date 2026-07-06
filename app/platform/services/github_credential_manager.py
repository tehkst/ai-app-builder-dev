from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List


DEFAULT_REPOSITORY = "tehkst/ai-app-builder-dev"
DEFAULT_SECRET_NAME = "GITHUB_TOKEN"
ALLOWED_WRITE_ACTIONS = [
    "create_feature_branch",
    "write_feature_branch_files",
    "commit_feature_branch_changes",
    "open_pull_request",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _token_present() -> bool:
    return bool(os.getenv(DEFAULT_SECRET_NAME))


def _mask_status() -> str:
    return "configured" if _token_present() else "missing"


def _secret_source() -> str:
    return os.getenv("GITHUB_TOKEN_SOURCE", "environment_or_secret_manager")


def github_credential_status() -> Dict[str, Any]:
    present = _token_present()
    return {
        "mode": "github_credential_manager_v1",
        "checked_at": _now(),
        "credential": {
            "secret_name": DEFAULT_SECRET_NAME,
            "secret_source": _secret_source(),
            "status": _mask_status(),
            "token_value_exposed": False,
            "token_present": present,
        },
        "repository_policy": {
            "default_repository": DEFAULT_REPOSITORY,
            "allowed_repositories": [DEFAULT_REPOSITORY],
            "direct_main_writes_allowed": False,
            "feature_branch_only": True,
            "requires_founder_approval_for_writes": True,
            "requires_external_review_before_merge": True,
        },
        "allowed_write_actions_after_approval": ALLOWED_WRITE_ACTIONS,
        "readiness": {
            "github_connected": present,
            "ready_for_repository_mutation_engine": present,
            "blocking_reason": None if present else "GITHUB_TOKEN is not configured in the runtime environment or Secret Manager binding.",
        },
        "audit_event": {
            "event": "github_credential_status_checked",
            "timestamp": _now(),
            "token_logged": False,
            "actor": "credential_manager",
        },
    }


def validate_repository_access_request(repository: str, action: str, approved: bool = False) -> Dict[str, Any]:
    status = github_credential_status()
    repository_allowed = repository in status["repository_policy"]["allowed_repositories"]
    action_allowed = action in ALLOWED_WRITE_ACTIONS
    credential_ready = status["credential"]["token_present"]
    approved_for_write = approved is True
    allowed = repository_allowed and action_allowed and credential_ready and approved_for_write
    reasons: List[str] = []
    if not repository_allowed:
        reasons.append("Repository is not in allowlist.")
    if not action_allowed:
        reasons.append("Action is not permitted by credential policy.")
    if not credential_ready:
        reasons.append("GitHub credential is not configured.")
    if not approved_for_write:
        reasons.append("Founder approval is required for write actions.")
    return {
        "mode": "github_repository_access_validation_v1",
        "repository": repository,
        "action": action,
        "approved": approved,
        "allowed": allowed,
        "reasons": reasons,
        "policy": status["repository_policy"],
        "checked_at": _now(),
    }


def github_connection_test() -> Dict[str, Any]:
    status = github_credential_status()
    return {
        "mode": "github_connection_test_v1",
        "status": "ready" if status["credential"]["token_present"] else "not_ready",
        "safe_to_log": True,
        "token_value_exposed": False,
        "repository": DEFAULT_REPOSITORY,
        "next_action": "Proceed to Repository Mutation Engine" if status["credential"]["token_present"] else "Configure GITHUB_TOKEN through Secret Manager or runtime environment.",
        "credential_status": status,
    }


def format_github_credential_markdown(status: Dict[str, Any]) -> str:
    credential = status.get("credential", {})
    readiness = status.get("readiness", {})
    policy = status.get("repository_policy", {})
    lines = [
        "## GitHub Credential Manager",
        "",
        f"**Credential status:** {credential.get('status')}",
        f"**Secret name:** {credential.get('secret_name')}",
        f"**Token exposed:** {credential.get('token_value_exposed')}",
        f"**Default repository:** {policy.get('default_repository')}",
        f"**Ready for Repository Mutation Engine:** {readiness.get('ready_for_repository_mutation_engine')}",
        "",
        "### Policy",
        f"- Feature branch only: {policy.get('feature_branch_only')}",
        f"- Direct main writes allowed: {policy.get('direct_main_writes_allowed')}",
        f"- Founder approval required: {policy.get('requires_founder_approval_for_writes')}",
        f"- External review before merge: {policy.get('requires_external_review_before_merge')}",
    ]
    if readiness.get("blocking_reason"):
        lines.extend(["", f"**Blocking reason:** {readiness.get('blocking_reason')}"])
    return "\n".join(lines)
