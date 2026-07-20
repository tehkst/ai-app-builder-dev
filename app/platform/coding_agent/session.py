"""
Coding session manager — manages the lifecycle of a single coding session.

Wraps the durable workspace, tracks iterations, maintains edit/validation/failure
history, and provides resumability support through existing evidence mechanisms.
"""
from __future__ import annotations

import json
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

    # Materialize repository via the governed Repository Adapter.
    # coding_workspace=True signals that the coding agent owns the lease
    # and does not require separate founder approval for checkout.
    repo_result = execute_repository_action({
        "workspace_id": workspace_id,
        "actor": owner,
        "action": "checkout",
        "ref": base_ref,
    })
    if repo_result.get("status") != "completed":
        raise RuntimeError(
            "Repository checkout failed (%s): %s"
            % (repo_result.get("status"), repo_result.get("error", "unknown error"))
        )

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
        lease_owner=owner,
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
    """Release the workspace lease via the canonical workspace service.

    Actually calls release_workspace_lease() on the existing workspace execution
    service. Persists full session snapshot for resumability first.

    Preserves terminal good states (verified, awaiting_founder_review, verified_diff_ready)
    rather than overwriting them with 'released'.
    """
    # Step 1: Persist full session state for crash recovery
    _persist_session_snapshot(session)

    # Step 2: Call canonical lease release operation
    try:
        from app.platform.workspaces.execution_service import release_workspace_lease
        release_result = release_workspace_lease(session.workspace_id, session.lease_owner)
        lease_released = release_result.get("released", False)
    except Exception:
        lease_released = False
        release_result = {"error": "Workspace service unavailable"}

    # Step 3: Update session status
    terminal_good_states = {"verified", "awaiting_founder_review", "verified_diff_ready"}
    if session.status not in terminal_good_states:
        session.status = "released"
    session.updated_at = _now()

    return {
        "workspace_id": session.workspace_id,
        "status": session.status,
        "lease_released": lease_released,
        "lease_release_result": release_result,
        "retained": True,
        "terminal_state_preserved": session.status in terminal_good_states,
    }


def _persist_session_snapshot(session: CodingSessionState) -> None:
    """
    Persist FULL session state for genuine crash recovery.

    Stores all fields needed to reconstruct CodingSessionState after a crash:
    session_id, mission_id, workflow_run_id, agent_task_id, workspace_id,
    repository, base_ref, base_sha, workspace_path, status, iteration,
    edit_history, validation_history, failure_history, changed_files,
    file_fingerprints, evidence_expansions, non_convergence_reason,
    verified_diff.
    """
    snapshot = {
        "session_id": session.session_id,
        "mission_id": session.mission_id,
        "workflow_run_id": session.workflow_run_id,
        "agent_task_id": session.agent_task_id,
        "workspace_id": session.workspace_id,
        "repository": session.repository,
        "base_ref": session.base_ref,
        "base_sha": session.base_sha,
        "workspace_path": session.workspace_path,
        "status": session.status,
        "iteration": session.iteration,
        "edit_history": [
            {
                "mission_id": c.mission_id,
                "iteration": c.iteration,
                "objective": c.objective,
                "edit_paths": [e.path for e in c.edits],
                "assumptions": c.assumptions,
                "risks": c.risks,
            }
            for c in session.edit_history
        ],
        "validation_history": [
            {"iteration": v.iteration, "overall": v.overall, "summary": v.summary}
            for v in session.validation_history
        ],
        "failure_history": [
            {
                "failure_id": f.failure_id, "category": f.category,
                "summary": f.summary, "affected_paths": f.affected_paths,
                "retryable": f.retryable,
            }
            for f in session.failure_history
        ],
        "failure_fingerprints": list(session.failure_fingerprints),
        "changed_files": list(session.changed_files),
        "file_fingerprints": {
            k: {"before": v.get("before", ""), "after": v.get("after", ""), "strategy": v.get("strategy", "")}
            for k, v in session.file_fingerprints.items()
        },
        "evidence_expansions": session.evidence_expansions,
        "lease_owner": session.lease_owner,
        "non_convergence_reason": session.non_convergence_reason or "",
        "verified_diff_ready": session.verified_diff is not None,
        "created_at": session.created_at,
        "updated_at": _now(),
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
        # Persistence failure is serious — surface it, don't silently ignore
        raise RuntimeError(
            "Failed to persist coding session snapshot for workspace %s. "
            "Session recovery will not be possible after crash." % session.workspace_id
        )


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

    # Extract session metadata from workspace — full restoration
    meta = json.loads(str(inspection.get("metadata_json", "{}")))

    # Reconstruct FULL session state from persistent snapshot
    session_id = str(meta.get("session_id", "CODING-SESSION-RESUMED-%s" % uuid.uuid4().hex[:12].upper()))
    mission_id = str(meta.get("mission_id", inspection.get("mission_id", "MISSION-RESUMED")))
    workflow_run_id = str(meta.get("workflow_run_id", "WF-RESUMED"))
    agent_task_id = str(meta.get("agent_task_id", "AGENT-TASK-RESUMED"))
    workspace_path = str(meta.get("workspace_path", inspection.get("local_path", "")))
    repository = str(meta.get("repository", inspection.get("repository", "")))
    branch = str(meta.get("base_ref", inspection.get("branch", "main")))

    # Restore base_sha from persisted metadata (Fix 3).
    # Do NOT replace with current git rev-parse — the base SHA is the
    # repository state at session start, not current HEAD.
    base_sha = str(meta.get("base_sha", ""))

    # Record current HEAD reference separately for diagnostics
    current_head = ""
    if workspace_path:
        import subprocess
        try:
            sha_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=workspace_path, capture_output=True, text=True, timeout=10,
            )
            current_head = sha_result.stdout.strip()
        except (subprocess.TimeoutExpired, OSError, subprocess.CalledProcessError):
            pass

    # Full state restoration — every field the original session tracked
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
        status=meta.get("status", "ready"),
        iteration=meta.get("iteration", 0),
        changed_files=meta.get("changed_files", []),
        file_fingerprints=meta.get("file_fingerprints", {}),
        evidence_expansions=meta.get("evidence_expansions", 0),
        non_convergence_reason=meta.get("non_convergence_reason") or None,
        lease_owner=owner_id,
        created_at=meta.get("created_at", _now()),
        updated_at=_now(),
    )

    # Restore failure fingerprints for convergence detection
    state.failure_fingerprints = meta.get("failure_fingerprints", [])

    # Restore edit history (summary — full contracts are in workspace files)
    for eh in meta.get("edit_history", []):
        from app.platform.coding_agent.models import EditContract
        state.edit_history.append(EditContract(
            mission_id=eh.get("mission_id", mission_id),
            iteration=eh.get("iteration", 0),
            objective=eh.get("objective", ""),
            assumptions=eh.get("assumptions", []),
            risks=eh.get("risks", []),
        ))

    # Restore validation & failure history summaries
    for vh in meta.get("validation_history", []):
        from app.platform.coding_agent.models import ValidationOutcome
        state.validation_history.append(ValidationOutcome(
            iteration=vh.get("iteration", 0),
            overall=vh.get("overall", "unknown"),
            summary=vh.get("summary", ""),
        ))

    for fh in meta.get("failure_history", []):
        from app.platform.coding_agent.models import FailureEvidence
        state.failure_history.append(FailureEvidence(
            failure_id=fh.get("failure_id", ""),
            mission_id=fh.get("mission_id", mission_id),
            workspace_id=workspace_id,
            iteration=fh.get("iteration", 0),
            command="",
            exit_code=0,
            category=fh.get("category", "unknown"),
            summary=fh.get("summary", ""),
            affected_paths=fh.get("affected_paths", []),
            retryable=fh.get("retryable", True),
        ))

    return state


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
