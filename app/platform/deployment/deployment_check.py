from __future__ import annotations

from app.platform.deployment.deployment_engine import execute_deployment, fail_deployment
from app.platform.deployment.deployment_events import deployment_result_event
from app.platform.deployment.deployment_metrics import deployment_metrics
from app.platform.deployment.deployment_pipeline import run_pipeline
from app.platform.deployment.deployment_planner import build_deployment_plan
from app.platform.deployment.deployment_recovery import NO_RECOVERY, RETRY_DEPLOYMENT, deployment_recovery_action
from app.platform.deployment.deployment_registry import deployment_registry, find_deployment_plan


def main() -> None:
    registry = deployment_registry()
    assert "local_deployment_plan" in registry, registry
    plan = find_deployment_plan("local_deployment_plan")
    assert plan.strategy == "validate_then_release", plan

    safe_plan = build_deployment_plan("app", "local", "safe_release")
    assert safe_plan.steps == ["validate", "package", "release", "verify"], safe_plan

    result = execute_deployment(safe_plan)
    assert result.status == "completed", result
    assert deployment_recovery_action(result) == NO_RECOVERY

    failed = fail_deployment(safe_plan, "temporary timeout")
    assert deployment_recovery_action(failed) == RETRY_DEPLOYMENT

    pipeline = run_pipeline(safe_plan)
    assert pipeline["status"] == "completed", pipeline
    assert pipeline["step_count"] == 4, pipeline

    event = deployment_result_event(result)
    assert event.source == "deployment", event

    metrics = deployment_metrics([result, failed])
    assert metrics["deployment_count"] == 2, metrics
    assert metrics["completed_deployment_count"] == 1, metrics
    assert metrics["failed_deployment_count"] == 1, metrics

    print("DEPLOYMENT CHECK PASSED")


if __name__ == "__main__":
    main()
