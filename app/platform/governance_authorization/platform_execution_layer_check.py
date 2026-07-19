from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

from app.platform.governance_authorization.approvals import create_durable_approval, consume_durable_approval
from app.platform.governance_authorization.capabilities import build_capability_matrix
from app.platform.governance_authorization.service import authorize_governed_action
from app.platform.persistence.execution_migrations import execution_schema_status, run_execution_layer_migrations
from app.platform.workspaces import execution_service
from app.platform.github_execution.service import execute_github_execution
from app.platform.execution.repository_adapter import _command as repository_command
from app.platform.github_execution.adapter import _request as github_request
from app.platform.release.execution_adapter import _request as release_request


def main() -> None:
    suffix = uuid.uuid4().hex[:10].upper()
    mission_id = "MISSION-P1-%s" % suffix
    workspace_id = "WORKSPACE-P1-%s" % suffix
    run_execution_layer_migrations()
    schema = execution_schema_status()
    assert schema["configured"] is True and len(schema["tables"]) == 4

    with patch("app.platform.governance_authorization.approvals.require_founder", return_value={"authorized": True, "founder_id": "founder"}):
        approval = create_durable_approval({"mission_id": mission_id, "action": "repository_fetch", "scope": "workspace", "target": workspace_id})
    first = consume_durable_approval(approval["approval_id"], mission_id, "repository_fetch", workspace_id)
    second = consume_durable_approval(approval["approval_id"], mission_id, "repository_fetch", workspace_id)
    assert first["consumed"] is True and second["consumed"] is False

    with patch("app.platform.governance_authorization.approvals.require_founder", return_value={"authorized": False}):
        denied_approval = create_durable_approval({"mission_id": mission_id, "action": "repository_pull", "scope": "workspace", "target": workspace_id})
    assert denied_approval["status"] == "denied"
    with patch("app.platform.governance_authorization.approvals.require_founder", return_value={"authorized": True, "founder_id": "founder"}):
        executable = create_durable_approval({"mission_id": mission_id, "action": "repository_pull", "scope": "workspace", "target": workspace_id})
    authorization_payload = {"mission_id": mission_id, "actor": "mission_control", "live_execution": True, "approval_id": executable["approval_id"], "target": workspace_id}
    evidence = {"evidence_id": "AUTH-CHECK", "observed_at": "now"}
    with patch("app.platform.governance_authorization.service.require_founder", return_value={"authorized": True}), patch("app.platform.governance_authorization.service.record_operational_evidence", return_value=evidence):
        authorized = authorize_governed_action(authorization_payload, "repository_pull", policy_context={"durable_approval_required": True})
        replay = authorize_governed_action(authorization_payload, "repository_pull", policy_context={"durable_approval_required": True})
    assert authorized["allowed"] is True and replay["denied"] is True

    with tempfile.TemporaryDirectory() as root:
        with patch.object(execution_service, "WORKSPACE_ROOT", Path(root)):
            workspace = execution_service.create_workspace({"workspace_id": workspace_id, "mission_id": mission_id, "owner_id": "mission_control", "repository": "tehkst/ai-app-builder-dev"})
            assert workspace["mission_id"] == mission_id
            lease = execution_service.acquire_workspace_lease(workspace_id, "mission_control", 60)
            blocked = execution_service.acquire_workspace_lease(workspace_id, "codex", 60)
            assert lease["acquired"] is True and blocked["acquired"] is False
            assert execution_service.heartbeat_workspace(workspace_id, "mission_control", 60)["renewed"] is True
            artifact = execution_service.record_workspace_artifact(workspace_id, "validation", "validation.txt", b"passed")
            assert len(artifact["sha256"]) == 64
            assert execution_service.destroy_workspace(workspace_id, "mission_control")["status"] == "destroyed"

    matrix = build_capability_matrix()
    assert len(matrix) == 35
    assert all(row["mission_control"] == row["codex"] for row in matrix)
    assert all(row["implemented"] is True for row in matrix)
    assert all("evidence" in row and "freshness" in row and "unknown_reason" in row for row in matrix)
    repository_payload = {"ref": "abc123", "remote": "origin", "confirm_destructive": True}
    repository_workspace = {"branch": "feature/check"}
    for action in ("checkout", "fetch", "pull", "merge", "rebase", "reset", "cherry_pick", "revert"):
        assert isinstance(repository_command(action, repository_payload, repository_workspace), list), action
    github_payload = {"pr_number": 12, "title": "Title", "body": "Review", "reviewers": ["founder"], "labels": ["release"], "milestone": 3}
    for action in ("update_pr", "review_pr", "request_changes", "approve_pr", "close_pr", "reopen_pr", "assign_reviewers", "labels", "milestones", "workflow_inspection"):
        assert isinstance(github_request(action, github_payload), tuple), action
    release_payload = {"tag_name": "v1.2.3", "target_commitish": "main", "release_id": 7, "base": "v1.2.2", "head": "v1.2.3", "commit_sha": "abc123"}
    for action in ("create_release", "promote_release", "rollback_release", "compare_releases", "release_notes", "release_history", "version_tag"):
        assert isinstance(release_request(action, release_payload), tuple), action
    with patch("app.platform.github_execution.approved_executor.execute_approved_github_execution", return_value={"status": "delegated"}) as delegated:
        legacy = execute_github_execution({"mission_id": mission_id, "live_execution": True, "approval_status": "approved", "branch_name": "feature/check", "commit_message": "Check", "pr_title": "Check", "write_batch": [{"path": "README.md", "content": "check"}]})
    assert legacy["status"] == "delegated" and delegated.call_count == 1
    print("Platform execution layer checks passed")


if __name__ == "__main__":
    main()
