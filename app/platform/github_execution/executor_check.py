from __future__ import annotations

import os

from app.platform.github_execution.service import (
    GITHUB_TOKEN_SECRET_NAME,
    build_github_execution_summary,
    execute_github_execution,
    plan_github_execution,
)


def main() -> None:
    original_token = os.environ.pop(GITHUB_TOKEN_SECRET_NAME, None)
    try:
        summary = build_github_execution_summary()
        assert summary["repository"] == "tehkst/ai-app-builder-dev"
        assert summary["github_token_present"] is False
        assert summary["github_token_visible"] is False
        assert summary["safety"]["main_branch_write_allowed"] is False
        assert summary["safety"]["founder_approval_required"] is True
        assert summary["safety"]["live_execution_requires_explicit_flag"] is True

        payload = {
            "mission_id": "GCP-02-CHECK",
            "title": "Verify live GitHub executor guardrails",
            "feature_branch": "mission/gcp-02-check",
            "base_branch": "main",
            "write_batch": [
                {
                    "path": "company/checks/gcp-02.md",
                    "operation": "create",
                    "content": "# GCP-02 check\n",
                }
            ],
            "approval": {
                "status": "approved",
                "approved_by": "founder",
                "approval_id": "APPROVAL-GCP-02-CHECK",
            },
        }

        plan = plan_github_execution(payload)
        assert plan["status"] == "github-execution-plan-created"
        assert plan["write_batch"][0]["content_present"] is True
        assert "content" not in plan["write_batch"][0]

        blocked = execute_github_execution({**payload, "feature_branch": "main"})
        assert blocked["status"] == "blocked-main-branch-write"
        assert blocked["writes_performed"] is False
        assert blocked["pull_request_created"] is False

        missing_token = execute_github_execution(payload)
        assert missing_token["status"] == "blocked-missing-github-token"
        assert missing_token["github_token_visible"] is False

        os.environ[GITHUB_TOKEN_SECRET_NAME] = "dummy-token-for-contract-check"
        dry_run = execute_github_execution(payload)
        assert dry_run["status"] == "dry-run-ready-for-live-github-execution"
        assert dry_run["writes_performed"] is False
        assert dry_run["pull_request_created"] is False
        assert "execution_contract" in dry_run

        print("GITHUB EXECUTION CHECK PASSED")
    finally:
        if original_token is None:
            os.environ.pop(GITHUB_TOKEN_SECRET_NAME, None)
        else:
            os.environ[GITHUB_TOKEN_SECRET_NAME] = original_token


if __name__ == "__main__":
    main()
