from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.platform.auth.service import require_founder
from app.platform.constitution.policy_engine import blocking_rules_for_target
from app.platform.persistence.operational_evidence import latest_operational_record, record_operational_evidence
from app.platform.governance_authorization.approvals import consume_durable_approval
from app.platform.governance_authorization.evidence import record_execution_evidence


POLICY = "capability-authority-separation-v1"
ACTORS = ("mission_control", "codex")
CAPABILITIES = {
    "repository": ("create_branch", "checkout", "commit", "push", "revert", "cherry_pick", "repository_checkout", "repository_fetch", "repository_pull", "repository_merge", "repository_rebase", "repository_reset", "repository_cherry_pick", "repository_revert"),
    "github": ("create_pr", "update_pr", "review_pr", "approve_pr", "merge_pr", "close_pr", "read_workflow_status", "github_update_pr", "github_review_pr", "github_request_changes", "github_approve_pr", "github_close_pr", "github_reopen_pr", "github_assign_reviewers", "github_labels", "github_milestones", "github_workflow_inspection"),
    "deployment": ("deploy", "rollback", "monitor_deployment", "production_verification"),
    "release": ("create_release", "promote_release", "view_release_history", "release_create_release", "release_promote_release", "release_rollback_release", "release_compare_releases", "release_release_notes", "release_release_history", "release_version_tag"),
    "workspace": ("workspace_create", "workspace_resume", "workspace_lock", "workspace_recover", "workspace_cleanup", "workspace_destroy"),
}
READ_ONLY = {"read_workflow_status", "monitor_deployment", "production_verification", "view_release_history", "github_workflow_inspection", "release_compare_releases", "release_release_notes", "release_release_history"}
TARGETS = {
    "merge_pr": "merge", "deploy": "deployment", "rollback": "deployment",
    "create_release": "release", "promote_release": "release",
}


def build_governance_authorization_summary() -> Dict[str, Any]:
    from app.platform.governance_authorization.capabilities import build_capability_matrix
    return {
        "status": "governance-authorization-ready",
        "policy": POLICY,
        "architectural_law": "Capability != Authority",
        "capability_matrix": build_capability_matrix(),
        "governance": {
            "self_authorization": False,
            "single_authorization_service": True,
            "durable_decision_evidence": True,
            "founder_approval_required_for_mutation": True,
        },
    }


def authorize_governed_action(
    payload: Dict[str, Any],
    capability: Optional[str] = None,
    *,
    required_approval_phrase: Optional[str] = None,
    policy_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    evaluated_at = _now()
    context = dict(policy_context or {})
    action = str(capability or payload.get("capability") or "").strip()
    actor = str(payload.get("actor") or payload.get("actor_type") or "mission_control").strip().lower()
    known = any(action in values for values in CAPABILITIES.values())
    read_only = action in READ_ONLY
    founder = require_founder(payload)
    approval_ok = read_only or (
        bool(founder.get("authorized"))
        and bool(payload.get("live_execution") is True)
        and (required_approval_phrase is None or payload.get("approval_phrase") == required_approval_phrase)
    )
    durable_approval = None
    if approval_ok and not read_only and payload.get("approval_id"):
        durable_approval = consume_durable_approval(
            str(payload.get("approval_id")), str(payload.get("mission_id") or ""), action,
            str(payload.get("target") or payload.get("workspace_id") or payload.get("pr_number") or payload.get("service_name") or payload.get("tag_name") or ""),
        )
        approval_ok = bool(durable_approval.get("consumed"))
    if not read_only and context.get("durable_approval_required") and durable_approval is None:
        approval_ok = False
    target = TARGETS.get(action, "workflow")
    rules = blocking_rules_for_target(target)
    evaluations = {
        "founder_approval": approval_ok,
        "governance_policy": known and actor in ACTORS,
        "release_gates": bool(context.get("release_gates", True)),
        "security_policy": bool(context.get("security_policy", True)),
        "execution_policy": bool(context.get("execution_policy", True)),
        "mission_state": bool(context.get("mission_state", read_only or payload.get("mission_id"))),
        "platform_state": bool(context.get("platform_state", True)),
        "destructive_operation_policy": bool(context.get("destructive_operation_policy", True)),
        "workspace_ownership": bool(context.get("workspace_ownership", True)),
    }
    allowed = all(evaluations.values())
    failed = [name.replace("_", " ") for name, passed in evaluations.items() if not passed]
    reason = "Governance authorization granted." if allowed else "Denied by: %s." % ", ".join(failed)
    required = [] if approval_ok else ["valid founder session", "live_execution=true", "action-scoped durable approval"]
    decision = {
        "allowed": allowed,
        "denied": not allowed,
        "reason": reason,
        "governing_policy": POLICY,
        "required_approvals": required,
        "evaluated_at": evaluated_at,
        "confidence": "high",
        "actor": actor,
        "capability": action,
        "requested_action": str(payload.get("requested_action") or action),
        "policy_evaluated": {"constitution_targets": [target], "blocking_rules": rules, "checks": evaluations},
        "durable_approval": durable_approval,
    }
    try:
        evidence = record_operational_evidence(
            "governance_authorization", "governance_authorization_layer",
            str(payload.get("mission_id") or action or "unknown"),
            "allowed" if allowed else "denied", _evidence_payload(payload, decision, None),
        )
        decision["evidence_id"] = evidence["evidence_id"]
    except Exception as exc:
        decision.update({"allowed": False, "denied": True, "reason": "Durable authorization evidence could not be recorded.", "confidence": "high", "evidence_error": type(exc).__name__})
    return decision


def record_governed_outcome(payload: Dict[str, Any], decision: Dict[str, Any], outcome: Dict[str, Any]) -> Dict[str, Any]:
    record = record_operational_evidence(
        "governed_execution", "governance_authorization_layer",
        str(payload.get("mission_id") or decision.get("capability") or "unknown"),
        str(outcome.get("status") or "completed"), _evidence_payload(payload, decision, outcome),
    )
    canonical = record_execution_evidence(payload, decision, outcome)
    return {"evidence_id": canonical["evidence_id"], "recorded_at": canonical["recorded_at"], "legacy_evidence_id": record["evidence_id"]}


def get_governance_evidence(payload: Dict[str, Any]) -> Dict[str, Any]:
    capability = str(payload.get("capability") or "").strip()
    record = latest_operational_record("governed_execution", capability or None)
    return {"status": "evidence-observed" if record else "unknown", "evidence": record}


def _evidence_payload(payload: Dict[str, Any], decision: Dict[str, Any], outcome: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    outcome = outcome or {}
    return {
        "actor": decision.get("actor"), "capability": decision.get("capability"),
        "requested_action": decision.get("requested_action"), "authorization_decision": decision,
        "policy_evaluated": decision.get("policy_evaluated"), "timestamp": _now(),
        "commit_sha": outcome.get("commit") or outcome.get("merge_commit_sha"),
        "pr": outcome.get("pull_request_number") or outcome.get("pr_number") or outcome.get("pull_request_url"),
        "deployment_revision": outcome.get("revision_name") or outcome.get("target_revision"),
        "production_verification": outcome.get("production_verification") or outcome.get("overall_result"),
        "outcome": outcome.get("status"),
    }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
