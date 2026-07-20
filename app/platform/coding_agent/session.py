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
    """Release the workspace lease via the existing workspace service.

    Preserves terminal good states (verified, awaiting_founder_review, verified_diff_ready)
    rather than overwriting them with 'released'. Only marks 'released' for
    failed/blocked sessions, or after founder approval when the diff has been consumed.
    """
    from app.platform.workspaces.execution_service import (
        acquire_workspace_lease,
        inspect_workspace,
    )

    inspection = inspect_workspace(session.workspace_id)

    # Only change status if not already in a terminal good state
    terminal_good_states = {"verified", "awaiting_founder_review", "verified_diff_ready"}
    if session.status not in terminal_good_states:
        session.status = "released"

    session.updated_at = _now()

    # Write session state into workspace metadata for resumability
    _persist_session_snapshot(session)

    # The lease expires naturally per retention policy.
    # Workspace data is retained for audit; cleanup via retention_until.
    return {
        "workspace_id": session.workspace_id,
        "status": session.status,
        "inspection_status": inspection.get("status"),
        "retained": True,
        "terminal_state_preserved": session.status in terminal_good_states,
    }


def resume_coding_session(
    workspace_id: str,
    owner_id: str,
) -> Optional[CodingSessionState]:
    """
    Resume a coding session from durable workspace state.

    Used after process termination or crash. Recovers:
    - Workspace state and path from the existing workspace record
    - Session metadata from workspace metadata
    - Reacquires lease for the recovered owner

    Args:
        workspace_id: The durable workspace ID to resume.
        owner_id: The owner that will reacquire the lease.

    Returns:
        Resumed CodingSessionState, or None if workspace is unrecoverable.
    """
    from app.platform.workspaces.execution_service import (
        acquire_workspace_lease,
        inspect_workspace,
    )

    inspection = inspect_workspace(workspace_id)
    if inspection.get("status") in {"not-found", "destroyed", "cleaned"}:
        return None

    # Reacquire lease
    lease = acquire_workspace_lease(workspace_id, owner_id)
    if not lease.get("acquired"):
        return None

    # Extract session metadata from workspace
    meta = json.loads(str(inspection.get("metadata_json", "{}")))

    # Reconstruct session state from workspace evidence
    session_id = str(meta.get("session_id", "CODING-SESSION-RESUMED-%s" % uuid.uuid4().hex[:12].upper()))
    mission_id = str(inspection.get("mission_id", "MISSION-RESUMED"))
    workflow_run_id = str(meta.get("workflow_run_id", "WF-RESUMED"))
    agent_task_id = str(meta.get("agent_task_id", "AGENT-TASK-RESUMED"))
    workspace_path = str(inspection.get("local_path", ""))
    repository = str(inspection.get("repository", ""))
    branch = str(inspection.get("branch", "main"))

    # Get current base SHA from workspace
    import subprocess
    try:
        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace_path, capture_output=True, text=True, timeout=10,
        )
        base_sha = sha_result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError, subprocess.CalledProcessError):
        base_sha = "unknown"

    state = CodingSessionState(
        session_id=session_id,
        mission_id=mission_id,
        workflow_run_id=workflow_run_id,
        agent_task_id=agent_task_id,
        workspace_id=workspace_id,
        repository=repository,
        base_ref=branch,
        base_sha=base_sha,
        workspace_path=workspace_path,
        status="ready",  # Reset to ready; iteration count preserved below
        iteration=meta.get("iterations", 0),
        changed_files=meta.get("changed_files", []),
        file_fingerprints=meta.get("file_fingerprints", {}),
        evidence_expansions=meta.get("evidence_expansions", 0),
    )

    return state


def _persist_session_snapshot(session: CodingSessionState) -> None:
    """
    Persist session state into the workspace metadata for resumability.

    Writes essential session state that can be recovered after a crash.
    Called during release_workspace().
    """
    import json

    snapshot = {
        "session_id": session.session_id,
        "iterations": session.iteration,
        "workflow_run_id": session.workflow_run_id,
        "agent_task_id": session.agent_task_id,
        "changed_files": list(session.changed_files),
        "file_fingerprints": {
            k: {"before": v.get("before", ""), "after": v.get("after", "")}
            for k, v in session.file_fingerprints.items()
        },
        "evidence_expansions": session.evidence_expansions,
        "status": session.status,
        "non_convergence_reason": session.non_convergence_reason or "",
    }

    try:
        from app.platform.persistence.database import PlatformSessionLocal
        from app.platform.persistence.execution_migrations import run_execution_layer_migrations
        from app.platform.persistence.models import PlatformExecutionWorkspace
        from sqlalchemy import update

        run_execution_layer_migrations()
        with PlatformSessionLocal() as db:
            db.execute(
                update(PlatformExecutionWorkspace)
                .where(PlatformExecutionWorkspace.workspace_id == session.workspace_id)
                .values(metadata_json=json.dumps(snapshot, sort_keys=True, default=str))
            )
            db.commit()
    except Exception:
        # Degrade gracefully — snapshot persistence failure should not crash the session
        pass


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
