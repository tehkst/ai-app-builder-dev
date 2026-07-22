from __future__ import annotations

from typing import Any

from app.platform.execution.service import get_execution_mission_evidence


STAGES = (
    "planning",
    "architecture_review",
    "engineering_handoff",
    "change_set",
    "repository_execution",
    "pull_request",
    "ci_validation",
    "ci_repair",
    "merge",
    "deployment",
    "production_verification",
)


def continue_mission_to_production(payload: dict[str, Any]) -> dict[str, Any]:
    """Project the next governed mission stage from existing authoritative evidence.

    This function is intentionally non-mutating. Existing authorities remain
    responsible for repository execution, CI repair, merge, deployment,
    rollback, traffic movement, and production verification.
    """

    mission_id = str(payload.get("mission_id") or "").strip()
    if not mission_id:
        return _blocked(None, "mission_identity", "A canonical mission_id is required.")

    evidence = get_execution_mission_evidence(mission_id) or {}
    if evidence.get("mission_id") != mission_id:
        return _blocked(mission_id, "mission_identity", "Canonical mission evidence was not found.")

    state = _derive_state(mission_id, evidence)
    return {
        "mission_id": mission_id,
        "status": "mission-completed" if state["completed"] else "mission-continuation-ready",
        "current_stage": state["current_stage"],
        "completed_stages": state["completed_stages"],
        "next_required_action": state["next_required_action"],
        "approval_required": state["approval_required"],
        "approval_action": state["approval_action"],
        "blocked_reason": state["blocked_reason"],
        "recovery_action": state["recovery_action"],
        "completion": {
            "completed": state["completed"],
            "verified_production": state["verified_production"],
        },
        "evidence": state["evidence"],
        "governance": {
            "read_only_projection": True,
            "repository_mutation": False,
            "merge": False,
            "deployment": False,
            "traffic_shift": False,
            "rollback": False,
            "source_systems_remain_authoritative": True,
            "separate_approvals_preserved": True,
        },
        "idempotency": {
            "reuses_existing_evidence": True,
            "repeated_request_without_new_evidence_returns_same_stage": True,
        },
    }


def _derive_state(mission_id: str, evidence: dict[str, Any]) -> dict[str, Any]:
    completed: list[str] = []
    selected: dict[str, Any] = {}

    def mark(stage: str, key: str, predicate: Any) -> bool:
        value = evidence.get(key) if isinstance(evidence.get(key), dict) else {}
        selected[key] = value
        ok = bool(predicate(value))
        if ok:
            completed.append(stage)
        return ok

    if not mark("planning", "planning_result", lambda value: value.get("status") == "engineering-plan-created"):
        return _state("planning", completed, selected, "Run the existing planning authority.")
    if not mark("architecture_review", "architecture_review", lambda value: value.get("status") == "architecture-reviewed"):
        return _state("architecture_review", completed, selected, "Run or resume the existing Architecture Agent review.")
    if not mark("engineering_handoff", "engineering_handoff", lambda value: value.get("status") == "engineering-breakdown-created"):
        return _state("engineering_handoff", completed, selected, "Run or resume the existing Engineering Manager handoff.")
    if not mark("change_set", "executable_change_set", lambda value: value.get("change_set_status") == "change_set_ready"):
        return _state("change_set", completed, selected, "Generate or repair the executable change set through the existing coding-agent path.")
    if not mark("repository_execution", "repository_execution", lambda value: value.get("status") == "pull-request-created"):
        return _state(
            "repository_execution",
            completed,
            selected,
            "Authorize repository mutation through the existing GitHub execution contract.",
            approval_required=True,
            approval_action="github_execution",
        )
    if not mark("pull_request", "pr_lifecycle_result", lambda value: value.get("mission_resolution_status") == "resolved"):
        return _state("pull_request", completed, selected, "Observe and resolve the existing pull request lifecycle.")

    ci = evidence.get("ci_validation") if isinstance(evidence.get("ci_validation"), dict) else {}
    selected["ci_validation"] = ci
    if ci.get("status") in {"failed", "blocked"}:
        repair = evidence.get("ci_repair") if isinstance(evidence.get("ci_repair"), dict) else {}
        selected["ci_repair"] = repair
        if repair.get("status") not in {"completed", "repaired", "passed"}:
            return _state("ci_repair", completed, selected, "Run the existing CI repair loop and re-check CI.", blocked_reason="CI validation failed.", recovery_action="resume_ci_repair")
        completed.append("ci_repair")
    elif ci.get("status") not in {"passed", "success", "completed"}:
        return _state("ci_validation", completed, selected, "Wait for or refresh existing CI validation evidence.")
    completed.append("ci_validation")

    if not mark("merge", "merge_result", lambda value: value.get("status") in {"merged", "merge-completed"}):
        return _state(
            "merge",
            completed,
            selected,
            "Authorize merge through the existing PR lifecycle authority.",
            approval_required=True,
            approval_action="merge",
        )
    if not mark("deployment", "deployment_result", lambda value: value.get("status") in {"deployed", "deployment-completed"}):
        deployment = selected.get("deployment_result") or {}
        blocked = deployment.get("status") in {"failed", "blocked"}
        return _state(
            "deployment",
            completed,
            selected,
            "Authorize deployment through the existing deployment authority." if not blocked else "Review deployment failure and existing rollback readiness before retrying.",
            approval_required=not blocked,
            approval_action="deployment" if not blocked else None,
            blocked_reason="Deployment failed." if blocked else None,
            recovery_action="review_rollback_readiness" if blocked else None,
        )
    if not mark("production_verification", "production_verification", lambda value: value.get("status") in {"verified", "passed", "production-verified"}):
        return _state("production_verification", completed, selected, "Run the existing production verification authority.")

    return {
        "current_stage": "completed",
        "completed_stages": STAGES,
        "next_required_action": "No action required. Mission is verified in production.",
        "approval_required": False,
        "approval_action": None,
        "blocked_reason": None,
        "recovery_action": None,
        "completed": True,
        "verified_production": True,
        "evidence": selected,
    }


def _state(
    current_stage: str,
    completed_stages: list[str],
    evidence: dict[str, Any],
    next_required_action: str,
    *,
    approval_required: bool = False,
    approval_action: str | None = None,
    blocked_reason: str | None = None,
    recovery_action: str | None = None,
) -> dict[str, Any]:
    return {
        "current_stage": current_stage,
        "completed_stages": tuple(completed_stages),
        "next_required_action": next_required_action,
        "approval_required": approval_required,
        "approval_action": approval_action,
        "blocked_reason": blocked_reason,
        "recovery_action": recovery_action,
        "completed": False,
        "verified_production": False,
        "evidence": evidence,
    }


def _blocked(mission_id: str | None, stage: str, reason: str) -> dict[str, Any]:
    return {
        "mission_id": mission_id,
        "status": "blocked",
        "current_stage": stage,
        "completed_stages": (),
        "next_required_action": reason,
        "approval_required": False,
        "approval_action": None,
        "blocked_reason": reason,
        "recovery_action": None,
        "completion": {"completed": False, "verified_production": False},
        "evidence": {},
        "governance": {"read_only_projection": True, "source_systems_remain_authoritative": True},
    }
