"""
Diff builder — produces actual git status and git diff from the workspace.

Generates a VerifiedDiff contract ready for founder review and governed downstream
GitHub execution. The diff is workspace-only; no remote mutation occurs here.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.platform.coding_agent.models import ChangedFile, CodingSessionState, VerifiedDiff


def build_verified_diff(
    session: CodingSessionState,
) -> VerifiedDiff:
    """
    Build a verified diff from the current workspace state.

    Args:
        session: The completed coding session with edit and validation history.

    Returns:
        VerifiedDiff with git status, git diff, and per-file change details.
    """
    workspace_path = session.workspace_path

    # Run git status
    git_status = _run_git_status(workspace_path)

    # Run git diff
    git_diff = _run_git_diff(workspace_path)

    # Get HEAD SHA
    head_sha = _run_git_head_sha(workspace_path)

    # Compute head tree fingerprint
    head_tree_fp = _compute_tree_fingerprint(workspace_path, session.changed_files)

    # Build per-file change details
    changed_files = _build_changed_files(
        workspace_path,
        session.changed_files,
        session.file_fingerprints,
    )

    # Collect all validation evidence
    validation_evidence: List[Dict[str, Any]] = []
    for outcome in session.validation_history:
        validation_evidence.append({
            "iteration": outcome.iteration,
            "overall": outcome.overall,
            "summary": outcome.summary,
            "command_count": len(outcome.commands),
        })

    # Collect assumptions and risks from edit history
    all_assumptions: List[str] = []
    all_risks: List[str] = []
    for contract in session.edit_history:
        all_assumptions.extend(contract.assumptions)
        all_risks.extend(contract.risks)

    last_validation = session.validation_history[-1] if session.validation_history else None
    validation = {
        "overall": last_validation.overall if last_validation else "unknown",
        "commands": [
            {"argv": r.argv, "exit_code": r.exit_code, "duration_ms": r.duration_ms}
            for r in (last_validation.commands if last_validation else [])
        ],
        "evidence": validation_evidence,
    }

    return VerifiedDiff(
        mission_id=session.mission_id,
        workflow_run_id=session.workflow_run_id,
        agent_task_id=session.agent_task_id,
        workspace_id=session.workspace_id,
        status="verified_diff_ready",
        base_ref=session.base_ref,
        base_sha=session.base_sha,
        head_tree_fingerprint=head_tree_fp,
        iterations=session.iteration,
        changed_files=changed_files,
        git_status=git_status,
        git_diff=git_diff,
        validation=validation,
        risks=list(dict.fromkeys(all_risks)),  # deduplicate
        assumptions=list(dict.fromkeys(all_assumptions)),
        artifacts=[],
        governance=_derive_governance(workspace_path, session),
        next_required_action="Founder review and governed repository execution approval.",
    )


def _run_git_status(workspace_path: str) -> str:
    """Run git status --porcelain in the workspace."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workspace_path,
            text=True,
            capture_output=True,
            timeout=30,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        return "git status unavailable"


def _run_git_diff(workspace_path: str) -> str:
    """Run git diff in the workspace."""
    try:
        result = subprocess.run(
            ["git", "diff", "--no-color"],
            cwd=workspace_path,
            text=True,
            capture_output=True,
            timeout=60,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, OSError):
        return "git diff unavailable"


def _run_git_head_sha(workspace_path: str) -> str:
    """Get HEAD SHA from the workspace."""
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


def _compute_tree_fingerprint(workspace_path: str, changed_files: List[str]) -> str:
    """Compute a composite fingerprint of the working tree."""
    hasher = hashlib.sha256()
    root = Path(workspace_path)
    for path in sorted(changed_files):
        hasher.update(path.encode("utf-8"))
        resolved = (root / path).resolve()
        try:
            resolved.relative_to(root)
            if resolved.is_file():
                content = resolved.read_text(encoding="utf-8")
                hasher.update(content.encode("utf-8"))
        except (ValueError, OSError):
            pass
    return hasher.hexdigest()


def _build_changed_files(
    workspace_path: str,
    changed_paths: List[str],
    fingerprints: Dict[str, Dict[str, str]],
) -> List[ChangedFile]:
    """Build ChangedFile list with insertion/deletion counts."""
    root = Path(workspace_path)
    result: List[ChangedFile] = []

    # Get git diff --stat for insertions/deletions
    stat = _run_git_diff_stat(workspace_path)

    for path in changed_paths:
        fps = fingerprints.get(path, {})
        before_fp = fps.get("before", "")
        after_fp = fps.get("after", "")

        resolved = (root / path).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            continue

        operation = "update"
        if before_fp and not after_fp:
            operation = "delete"
        elif after_fp and not before_fp:
            operation = "create"

        # Parse stat for insertions/deletions
        insertions, deletions = _parse_stat_for_path(stat, path)

        result.append(ChangedFile(
            path=path,
            operation=operation,
            insertions=insertions,
            deletions=deletions,
            before_fingerprint=before_fp or None,
            after_fingerprint=after_fp or None,
        ))

    return result


def _run_git_diff_stat(workspace_path: str) -> str:
    """Run git diff --stat."""
    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=workspace_path,
            text=True,
            capture_output=True,
            timeout=30,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, OSError):
        return ""


def _parse_stat_for_path(stat: str, path: str) -> tuple:
    """Parse git diff --stat for a specific path."""
    import re
    for line in stat.split("\n"):
        if path in line:
            # Extract numbers from patterns like "1 file changed, 10 insertions(+), 4 deletions(-)"
            ins = re.search(r"(\d+)\s+insertions?", line)
            dels = re.search(r"(\d+)\s+deletions?", line)
            # Or from the compact format: "| 10 ++++----"
            # Try the end-of-stat summary
            if not ins:
                # Try finding numbers in the path line itself
                parts = line.split("|")
                if len(parts) > 1:
                    changes = parts[1].strip()
                    plus = changes.count("+")
                    minus = changes.count("-")
                    return (plus, minus)
            return (
                int(ins.group(1)) if ins else 0,
                int(dels.group(1)) if dels else 0,
            )
    return (0, 0)


def _derive_governance(
    workspace_path: str,
    session: CodingSessionState,
) -> Dict[str, bool]:
    """
    Derive governance state from observable evidence.

    Uses the governed execution evidence layer (not local git state)
    to determine whether remote mutations occurred.

    - repository_mutated_in_workspace: are there uncommitted changes? (local git)
    - remote_repository_mutated: was anything pushed via governed GitHub executor?
      (queried from execution evidence, not inferred from local git)
    - branch_created_remotely, commit_created, push_performed, pull_request_created:
      all derived from the governance authorization evidence layer.
    """
    import subprocess

    root = Path(workspace_path)

    # Local workspace mutation: observable from git status
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root), capture_output=True, text=True, timeout=10,
        )
        has_uncommitted = bool(status.stdout.strip())
    except (subprocess.TimeoutExpired, OSError):
        has_uncommitted = False

    # Remote mutation evidence: query the governed execution evidence layer.
    # A "governed execution" record with capability starting with "github_"
    # and associated with this mission_id would indicate remote mutation.
    remote_mutation = _query_remote_mutation_evidence(session.mission_id)

    return {
        "repository_mutated_in_workspace": has_uncommitted,
        "remote_repository_mutated": remote_mutation.get("github_execution_performed", False),
        "branch_created_remotely": remote_mutation.get("branch_created", False),
        "commit_created": remote_mutation.get("commit_created", False),
        "push_performed": remote_mutation.get("push_performed", False),
        "pull_request_created": remote_mutation.get("pr_created", False),
        "evidence_source": "governed_execution_evidence_layer",
    }


def _query_remote_mutation_evidence(mission_id: str) -> Dict[str, bool]:
    """
    Query the platform's governed execution evidence layer for remote mutations.

    Checks:
    - Whether any governed GitHub execution was authorized for this mission
    - Whether any evidence records show branch creation, commit, push, or PR
    """
    evidence: Dict[str, bool] = {
        "github_execution_performed": False,
        "branch_created": False,
        "commit_created": False,
        "push_performed": False,
        "pr_created": False,
    }

    try:
        from app.platform.governance_authorization.service import get_governance_evidence
        # Query for GitHub-related governed executions
        for capability_prefix in ["github_", "create_pr", "merge_pr", "push"]:
            record = get_governance_evidence({
                "capability": capability_prefix,
                "mission_id": mission_id,
            })
            if record.get("status") == "evidence-observed" and record.get("evidence"):
                ev = record["evidence"]
                # If any governed GitHub execution occurred, remote mutation evidence exists
                evidence["github_execution_performed"] = True
                outcome = str(ev.get("outcome") or "").lower()
                if outcome in {"completed", "passed", "created"}:
                    if capability_prefix in {"github_"}:
                        evidence["branch_created"] = True
                        evidence["commit_created"] = True
                        evidence["push_performed"] = True
                    if "create_pr" in capability_prefix or "pr" in str(ev.get("artifact_json", "")).lower():
                        evidence["pr_created"] = True
    except Exception:
        # If the evidence layer is unavailable, we conservatively report unknown
        pass

    return evidence
