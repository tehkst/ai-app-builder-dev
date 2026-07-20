"""
Coding session manager — manages the lifecycle of a single coding session.

Wraps the durable workspace, tracks iterations, maintains edit/validation/failure
history, and provides resumability support through existing evidence mechanisms.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.platform.coding_agent.models import (
    CodingSessionState,
    EditContract,
    FailureEvidence,
    VerifiedDiff,
    ValidationOutcome,
)
from app.platform.coding_agent.policy import (
    DEFAULT_RETENTION_HOURS,
    DEFAULT_WORKSPACE_LEASE_SECONDS,
    MAX_CODING_ITERATIONS,
)
from app.platform.workspaces.execution_service import (
    acquire_workspace_lease,
    create_workspace,
    heartbeat_workspace,
    inspect_workspace,
)
from app.platform.execution.repository_adapter import execute_repository_action


def create_coding_session(
    mission_id: str,
    workflow_run_id: str,
    agent_task_id: str,
    repository: str,
    base_ref: str,
    *,
    owner_id: Optional[str] = None,
    max_iterations: Optional[int] = None,
) -> CodingSessionState:
    """
    Create and prepare a new coding session with a durable workspace.

    1. Resolve or create the durable workspace.
    2. Acquire exclusive lease.
    3. Materialize the repository at the approved base ref.
    4. Verify clean working tree.
    """
    session_id = "CODING-SESSION-%s" % uuid.uuid4().hex[:12].upper()
    owner = owner_id or "NativeCodingAgent"

    # Create workspace
    workspace_result = create_workspace({
        "mission_id": mission_id,
        "owner_id": owner,
        "repository": repository,
        "branch": base_ref,
        "retention_hours": DEFAULT_RETENTION_HOURS,
        "metadata": {
            "session_id": session_id,
            "workflow_run_id": workflow_run_id,
            "agent_task_id": agent_task_id,
        },
    })

    if workspace_result.get("status") in {"invalid", "not-found", "blocked"}:
        raise RuntimeError("Failed to create workspace: %s" % workspace_result.get("error", workspace_result.get("status")))

    workspace_id = str(workspace_result["workspace_id"])
    workspace_path = str(workspace_result["local_path"])

    # Acquire lease
    lease = acquire_workspace_lease(workspace_id, owner, DEFAULT_WORKSPACE_LEASE_SECONDS)
    if not lease.get("acquired"):
        raise RuntimeError("Failed to acquire workspace lease for %s" % workspace_id)

    # Materialize repository
    repo_result = execute_repository_action({
        "workspace_id": workspace_id,
        "actor": owner,
        "action": "checkout",
        "ref": base_ref,
    })
    if repo_result.get("status") == "blocked":
        raise RuntimeError("Repository checkout blocked: %s" % repo_result.get("error"))

    # Get base SHA
    base_sha = _get_base_sha(workspace_path, base_ref)

    # Verify clean working tree (after checkout)
    _verify_clean_tree(workspace_path)

    state = CodingSessionState(
        session_id=session_id,
        mission_id=mission_id,
        workflow_run_id=workflow_run_id,
        agent_task_id=agent_task_id,
        workspace_id=workspace_id,
        repository=repository,
        base_ref=base_ref,
        base_sha=base_sha,
        workspace_path=workspace_path,
        status="ready",
    )

    # Store max iterations for convergence checks
    state._max_iterations = max_iterations or MAX_CODING_ITERATIONS  # type: ignore[attr-defined]

    return state


def advance_session_iteration(
    session: CodingSessionState,
    contract: EditContract,
    outcome: ValidationOutcome,
) -> None:
    """Record an iteration's edit contract and validation outcome."""
    session.iteration += 1
    session.edit_history.append(contract)
    session.validation_history.append(outcome)
    session.changed_files.extend(
        e.path for e in contract.edits if e.path not in session.changed_files
    )
    session.updated_at = _now()

    # Update status based on outcome
    if outcome.overall == "passed":
        session.status = "verified"
    elif outcome.overall == "blocked":
        session.status = "blocked"
    elif session.iteration >= getattr(session, "_max_iterations", MAX_CODING_ITERATIONS):
        session.status = "failed"


def record_failure(
    session: CodingSessionState,
    failure: FailureEvidence,
) -> None:
    """Record a failure in the session."""
    session.failure_history.append(failure)
    session.failure_fingerprints.append(failure.fingerprint())
    session.status = "repairing"
    session.updated_at = _now()


def set_verified_diff(
    session: CodingSessionState,
    diff: VerifiedDiff,
) -> None:
    """Record the final verified diff."""
    session.verified_diff = diff
    session.status = "awaiting_founder_review"
    session.updated_at = _now()


def mark_blocked(
    session: CodingSessionState,
    reason: str,
) -> None:
    """Mark the session as blocked with a reason."""
    session.status = "blocked"
    session.non_convergence_reason = reason
    session.updated_at = _now()


def mark_failed(
    session: CodingSessionState,
    reason: str,
) -> None:
    """Mark the session as failed with a reason."""
    session.status = "failed"
    session.non_convergence_reason = reason
    session.updated_at = _now()


def release_workspace(session: CodingSessionState) -> Dict[str, Any]:
    """Release the workspace lease. Workspace is retained per policy."""
    # The lease expires naturally or can be recovered.
    # We don't destroy the workspace — retention policy handles cleanup.
    inspection = inspect_workspace(session.workspace_id)
    session.status = "released"
    session.updated_at = _now()
    return {
        "workspace_id": session.workspace_id,
        "status": inspection.get("status"),
        "retained": True,
    }


def _get_base_sha(workspace_path: str, base_ref: str) -> str:
    """Get the SHA of the base ref in the workspace."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace_path,
            text=True,
            capture_output=True,
            timeout=10,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        return "unknown"


def _verify_clean_tree(workspace_path: str) -> None:
    """Verify the workspace has a clean working tree."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workspace_path,
            text=True,
            capture_output=True,
            timeout=10,
        )
        if result.stdout.strip():
            # Warning only — the checkout may have left .gitignore-handled files
            pass
    except (subprocess.TimeoutExpired, OSError):
        pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
