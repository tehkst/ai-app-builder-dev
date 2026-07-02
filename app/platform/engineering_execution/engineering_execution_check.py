from __future__ import annotations

from app.platform.engineering_execution.service import build_engineering_execution_summary, execute_engineering_execution, get_engineering_execution_status, plan_engineering_execution


def main() -> None:
    summary = build_engineering_execution_summary()
    assert summary["milestone"] == "AEL-05"
    assert summary["status"] == "engineering-execution-ready"
    assert summary["governance"]["main_branch_write_allowed"] is False
    assert summary["governance"]["auto_merge_allowed"] is False

    payload = {
        "mission_id": "AEL-05-CHECK",
        "title": "Verify Engineering Execution Engine",
        "goal": "Prove Mission Control can plan and gate engineering execution.",
        "feature_branch": "mission/ael-05-check",
        "write_batch": [{"path": "company/checks/ael-05.md", "operation": "create", "content": "# AEL-05 check\n"}],
    }

    plan = plan_engineering_execution(payload)
    assert plan["status"] == "engineering-execution-plan-created"
    assert plan["github_execution_plan"]["status"] == "github-execution-plan-created"

    blocked = execute_engineering_execution(payload)
    assert blocked["status"] == "blocked-awaiting-founder-approval"

    status = get_engineering_execution_status({"execution_id": "ENGEXEC-CHECK"})
    assert status["status"] == "tracked"
    assert status["merge_allowed"] is False

    print("ENGINEERING EXECUTION CHECK PASSED")


if __name__ == "__main__":
    main()
