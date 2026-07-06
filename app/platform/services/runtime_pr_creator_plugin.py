from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pr_body(goal: str, repository_package: Dict[str, Any]) -> str:
    edits = repository_package.get("edit_operations", [])
    edit_lines = "\n".join(
        f"- `{edit.get('path')}` — {edit.get('operation', 'modify')}"
        for edit in edits
    ) or "- No file edits were produced yet."
    return (
        "## Mission Control PR\n\n"
        f"**Goal**\n\n{goal}\n\n"
        "## Proposed Changes\n\n"
        f"{edit_lines}\n\n"
        "## Governance\n\n"
        "- Founder approval required before merge.\n"
        "- External review required before merge.\n"
        "- Auto-merge disabled.\n"
        "- Auto-deploy disabled.\n"
    )


def build_runtime_pr_creator_plugin(goal: str, repository_package: Dict[str, Any], requested_by: str = "founder") -> Dict[str, Any]:
    edits: List[Dict[str, Any]] = repository_package.get("edit_operations", []) or []
    branch = repository_package.get("proposed_branch")
    repository = repository_package.get("repository") or "tehkst/ai-app-builder-dev"
    ready = bool(branch and edits)
    return {
        "roadmap_item": "BR-EXEC-03",
        "name": "PR Creator",
        "status": "pr_package_ready" if ready else "blocked_pending_repository_package",
        "goal": goal,
        "requested_by": requested_by,
        "created_at": _now(),
        "repository": repository,
        "base_branch": repository_package.get("base_branch", "main"),
        "head_branch": branch,
        "pr_title": repository_package.get("review_package", {}).get("pull_request_title") or f"Mission Control: {goal[:90]}",
        "pr_body": _pr_body(goal, repository_package),
        "draft": True,
        "maintainer_can_modify": True,
        "readiness": {
            "repository_package_present": bool(repository_package),
            "branch_present": bool(branch),
            "edits_present": bool(edits),
            "ready_to_open_pr_after_branch_commit": ready,
        },
        "execution_policy": {
            "create_pr_after_founder_approval": True,
            "auto_merge": False,
            "auto_deploy": False,
            "requires_founder_approval": True,
            "requires_external_review": True,
        },
        "next_action": {
            "owner": "founder" if ready else "mission_control",
            "action": "Approve PR creation after branch and commit are ready." if ready else "Complete repository package before PR creation.",
        },
        "audit_trail": [
            {"event": "pr_creator_package_created", "timestamp": _now(), "actor": "pr_creator_plugin"},
            {"event": "auto_merge_disabled", "timestamp": _now(), "actor": "governance"},
            {"event": "founder_review_required", "timestamp": _now(), "actor": "governance"},
        ],
    }
