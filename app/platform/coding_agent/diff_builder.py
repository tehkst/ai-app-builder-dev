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
        governance={
            "repository_mutated_in_workspace": True,
            "remote_repository_mutated": False,
            "branch_created_remotely": False,
            "commit_created": False,
            "push_performed": False,
            "pull_request_created": False,
        },
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
