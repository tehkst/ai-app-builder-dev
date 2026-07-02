from __future__ import annotations

from app.platform.auth_boundary.policy import build_auth_boundary_policy, is_auth_boundary_path, validate_auth_boundary
from app.platform.code_planner.service import DEFAULT_VALIDATION_GATES, validate_code_proposal
from app.platform.github_execution.service import execute_github_execution, plan_github_execution


def main() -> None:
    policy = build_auth_boundary_policy()
    assert policy["milestone"] == "PROTECT-01"
    assert policy["status"] == "auth-boundary-policy-ready"

    assert is_auth_boundary_path("app/platform/auth/service.py") is True
    assert is_auth_boundary_path("app/platform/ui/founder_dashboard_stable.py") is True
    assert is_auth_boundary_path("app/platform/conversation_intelligence/service.py") is False

    blocked = validate_auth_boundary(
        {
            "mission_type": "engineering",
            "approval_status": "approved",
            "files": ["app/platform/auth/service.py"],
        }
    )
    assert blocked["status"] == "blocked-auth-boundary-change"
    assert blocked["allowed"] is False

    allowed_non_auth = validate_auth_boundary(
        {
            "mission_type": "engineering",
            "approval_status": "approved",
            "files": ["app/platform/conversation_intelligence/service.py"],
        }
    )
    assert allowed_non_auth["status"] == "auth-boundary-pass"
    assert allowed_non_auth["allowed"] is True

    allowed_auth = validate_auth_boundary(
        {
            "mission_type": "authentication",
            "approval_status": "approved",
            "files": ["app/platform/auth/service.py"],
        }
    )
    assert allowed_auth["allowed"] is True

    code_validation = validate_code_proposal(
        {
            "mission_type": "engineering",
            "patch_proposal": {
                "proposed_changes": [{"path": "app/platform/auth/service.py"}],
                "validation_gates": DEFAULT_VALIDATION_GATES,
            },
        }
    )
    assert code_validation["status"] == "validation-failed"

    plan = plan_github_execution(
        {
            "mission_type": "engineering",
            "approval_status": "approved",
            "write_batch": [{"path": "app/platform/auth/service.py", "content": "x"}],
        }
    )
    assert plan["status"] == "github-execution-plan-blocked-auth-boundary"

    execution = execute_github_execution(
        {
            "mission_type": "engineering",
            "approval_status": "approved",
            "write_batch": [{"path": "app/platform/auth/service.py", "content": "x"}],
        }
    )
    assert execution["status"] == "blocked-auth-boundary-change"

    print("AUTH BOUNDARY POLICY CHECK PASSED")


if __name__ == "__main__":
    main()
