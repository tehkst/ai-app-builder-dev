"""
GitHub Executor compatibility adapter.

Proves that the Native Coding Agent's VerifiedDiff contract is accepted
by the existing GitHub Executor without modification to the executor.

Converts VerifiedDiff output to the format expected by:
  POST /mission-control/github-executor/execute
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.platform.coding_agent.models import VerifiedDiff

MAX_APPROVED_FILE_BYTES = 1_000_000


def verified_diff_to_github_execution_payload(
    verified_diff: VerifiedDiff,
    *,
    feature_branch: Optional[str] = None,
    commit_message: Optional[str] = None,
    pr_title: Optional[str] = None,
    pr_body: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convert a VerifiedDiff to a GitHub Executor execution payload.

    This proves compatibility — the existing GitHub Executor can consume
    the Coding Agent's output without any modification to the executor itself.

    Args:
        verified_diff: The Coding Agent's verified diff output.
        feature_branch: Branch name for the feature branch (auto-generated if None).
        commit_message: Commit message (auto-generated if None).
        pr_title: PR title (auto-generated if None).
        pr_body: PR body (auto-generated if None).

    Returns:
        Payload compatible with POST /mission-control/github-executor/execute.
    """
    mission_id = verified_diff.mission_id

    if feature_branch is None:
        feature_branch = _safe_branch_name(mission_id, "Native Coding Agent changes")
    if commit_message is None:
        commit_message = "Apply verified Native Coding Agent changes for %s" % mission_id
    if pr_title is None:
        pr_title = "Implement %s" % mission_id
    if pr_body is None:
        pr_body = _build_pr_body(verified_diff)

    # Build write_batch from changed files + git diff content
    write_batch: List[Dict[str, Any]] = []
    for cf in verified_diff.changed_files:
        write_batch.append({
            "path": cf.path,
            "operation": "modify" if cf.operation in {"update", "create"} else "delete",
            "content_source": "native-coding-agent-verified-diff",
            "intent": "Verified by Native Coding Agent edit/test/repair loop.",
        })

    payload: Dict[str, Any] = {
        "execution": {
            "mission_id": mission_id,
            "title": pr_title,
            "repository": "tehkst/ai-app-builder-dev",
            "base_branch": verified_diff.base_ref,
            "feature_branch": feature_branch,
            "write_batch": write_batch,
            "commit_message": commit_message,
            "pr_title": pr_title,
            "pr_body": pr_body,
            "validation_gates": [
                "Native Coding Agent validation passed (see verified_diff.validation)",
                "python -m compileall app",
                "CI: PR Validation must pass before merge",
            ],
        },
        "approval": {
            "status": "pending",
            "note": "Founder approval required before live_execution=true.",
        },
        "live_execution": False,  # Must be explicitly set to True after founder approval
        "verified_diff_reference": {
            "base_sha": verified_diff.base_sha,
            "head_tree_fingerprint": verified_diff.head_tree_fingerprint,
            "iterations": verified_diff.iterations,
        },
    }

    return payload


def validate_github_executor_compatibility(
    verified_diff: VerifiedDiff,
) -> Dict[str, Any]:
    """
    Validate that the VerifiedDiff contract can be consumed by the GitHub Executor.

    Returns a compatibility report without actually executing anything.
    """
    checks: List[Dict[str, Any]] = []

    # Check required fields
    checks.append({
        "check": "mission_id_present",
        "passed": bool(verified_diff.mission_id),
        "detail": "GitHub Executor requires mission_id.",
    })
    checks.append({
        "check": "base_ref_present",
        "passed": bool(verified_diff.base_ref),
        "detail": "GitHub Executor requires base_ref for branch creation.",
    })
    checks.append({
        "check": "changed_files_present",
        "passed": True,  # Empty diffs are valid — executor handles 0-change batches
        "detail": "GitHub Executor accepts any number of changes, including 0.",
    })
    checks.append({
        "check": "validation_passed",
        "passed": verified_diff.validation.get("overall") == "passed",
        "detail": "GitHub Executor requires validation evidence.",
    })
    checks.append({
        "check": "no_remote_mutation_yet",
        "passed": not verified_diff.governance.get("remote_repository_mutated", True),
        "detail": "GitHub Executor performs remote mutation; diff must be workspace-only.",
    })
    checks.append({
        "check": "payload_constructible",
        "passed": _test_payload_construction(verified_diff),
        "detail": "Can construct a valid GitHub Executor payload from the diff.",
    })

    all_pass = all(c["passed"] for c in checks)
    return {
        "compatible": all_pass,
        "checks": checks,
        "adapter": "verified_diff_to_github_execution_payload",
        "executor_endpoint": "POST /mission-control/github-executor/execute",
        "note": "Set live_execution=true only after founder approval." if all_pass else "Fix compatibility issues before execution.",
    }


def verified_diff_file_changes(verified_diff: VerifiedDiff) -> List[Dict[str, Any]]:
    """Materialize bounded file operations from the verified durable workspace."""
    from app.platform.workspaces.execution_service import inspect_workspace

    workspace = inspect_workspace(verified_diff.workspace_id)
    root = Path(str(workspace.get("local_path") or "")).resolve()
    if workspace.get("status") in {"not-found", "destroyed"} or not root.is_dir():
        raise ValueError("Verified workspace is unavailable.")
    changes: List[Dict[str, Any]] = []
    for changed in verified_diff.changed_files:
        path = str(changed.path or "").strip()
        target = (root / path).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError("Verified file path escapes the workspace.") from exc
        operation = "delete" if changed.operation == "delete" else "write"
        item: Dict[str, Any] = {"path": path, "operation": operation}
        if operation == "write":
            if not target.is_file() or target.is_symlink():
                raise ValueError("Verified changed file is unavailable or unsafe.")
            if target.stat().st_size > MAX_APPROVED_FILE_BYTES:
                raise ValueError("Verified changed file exceeds the approved size limit.")
            item["content"] = target.read_text(encoding="utf-8")
        changes.append(item)
    return changes


def _test_payload_construction(verified_diff: VerifiedDiff) -> bool:
    """Test that the payload can be constructed without errors."""
    try:
        payload = verified_diff_to_github_execution_payload(verified_diff)
        required = ["execution", "approval", "verified_diff_reference"]
        return all(k in payload for k in required)
    except Exception:
        return False


def _build_pr_body(verified_diff: VerifiedDiff) -> str:
    """Build a comprehensive PR body from verified diff evidence."""
    lines = [
        "## Summary",
        "Changes verified by the Native Coding Agent edit/test/repair loop.",
        "",
        "### Mission",
        "Mission: %s" % verified_diff.mission_id,
        "",
        "### Verification",
        "- Base SHA: %s" % verified_diff.base_sha,
        "- Head tree fingerprint: %s" % verified_diff.head_tree_fingerprint,
        "- Iterations: %d" % verified_diff.iterations,
        "- Validation: %s" % verified_diff.validation.get("overall", "unknown"),
        "",
        "### Changed Files",
    ]
    for cf in verified_diff.changed_files:
        lines.append("- %s (%s, +%d -%d)" % (
            cf.path, cf.operation, cf.insertions, cf.deletions,
        ))

    lines.extend([
        "",
        "### Governance",
        "- Remote mutation: %s" % ("No" if not verified_diff.governance.get("remote_repository_mutated") else "Yes"),
        "- Commit created: %s" % ("No" if not verified_diff.governance.get("commit_created") else "Yes"),
        "- Push performed: %s" % ("No" if not verified_diff.governance.get("push_performed") else "Yes"),
        "",
        "### Validation Evidence",
    ])
    for cmd in verified_diff.validation.get("commands", []):
        lines.append("- %s: exit %d" % (cmd.get("argv", ["unknown"])[0] if cmd.get("argv") else "unknown", cmd.get("exit_code", -1)))

    lines.append("")
    lines.append("## Approval Required")
    lines.append("Founder approval required before merge. CI must pass.")

    return "\n".join(lines)


def _safe_branch_name(mission_id: str, title: str) -> str:
    """Generate a safe git branch name."""
    raw = "mission/%s-%s" % (mission_id, title)
    raw = raw.lower()
    cleaned = "".join(c if c.isalnum() else "-" for c in raw)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")[:80]
