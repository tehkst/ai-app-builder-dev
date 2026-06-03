import json

from app.platform.persistence.crud import (
    complete_generation_run,
    create_generation_run,
    fail_generation_run,
    list_generation_runs_for_project,
)
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables


TENANT_ID = "generation-run-test-tenant"
WORKSPACE_ID = "generation-run-test-workspace"
PROJECT_ID = "generation-run-test-project"


def validate_generation_runs():
    create_platform_tables()
    db = PlatformSessionLocal()

    try:
        completed_run = create_generation_run(
            db,
            tenant_id=TENANT_ID,
            workspace_id=WORKSPACE_ID,
            project_id=PROJECT_ID,
            metadata={"case": "completed"},
        )
        completed_run = complete_generation_run(
            db,
            run_id=completed_run.run_id,
            review_status="PASS",
            runtime_status="passed",
            metadata={"case": "completed", "result": "ok"},
        )

        failed_run = create_generation_run(
            db,
            tenant_id=TENANT_ID,
            workspace_id=WORKSPACE_ID,
            project_id=PROJECT_ID,
            metadata={"case": "failed"},
        )
        failed_run = fail_generation_run(
            db,
            run_id=failed_run.run_id,
            error_summary="Validation test failure",
            review_status="FAIL",
            runtime_status="failed",
            metadata={"case": "failed", "result": "expected_failure"},
        )

        runs = list_generation_runs_for_project(
            db,
            tenant_id=TENANT_ID,
            workspace_id=WORKSPACE_ID,
            project_id=PROJECT_ID,
        )

        passed = (
            completed_run.status == "completed"
            and completed_run.review_status == "PASS"
            and completed_run.runtime_status == "passed"
            and completed_run.completed_at is not None
            and failed_run.status == "failed"
            and failed_run.error_summary == "Validation test failure"
            and len(runs) >= 2
        )

        return {
            "passed": passed,
            "completed_run_id": completed_run.run_id,
            "completed_status": completed_run.status,
            "failed_run_id": failed_run.run_id,
            "failed_status": failed_run.status,
            "run_count_for_project": len(runs),
        }

    finally:
        db.close()


def main():
    report = validate_generation_runs()
    print(json.dumps(report, indent=2, default=str))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
