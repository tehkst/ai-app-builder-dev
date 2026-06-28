from __future__ import annotations

from app.platform.deployment.deployment_engine import execute_deployment, fail_deployment
from app.platform.deployment.deployment_planner import build_deployment_plan
from app.platform.operations.deployment_dashboard import deployment_panel
from app.platform.operations.health_dashboard import health_panel
from app.platform.operations.incident_registry import add_incident, incident_registry, open_incidents
from app.platform.operations.operations_metrics import operations_metrics
from app.platform.operations.operations_models import OperationsIncident
from app.platform.operations.runtime_dashboard import runtime_panel


def main() -> None:
    health = health_panel([{"name": "runtime", "passed": True}])
    assert health.status == "healthy", health

    runtime = runtime_panel([], [])
    assert runtime.value == "0 jobs / 0 workers", runtime

    plan = build_deployment_plan("app", "local", "safe_release")
    done = execute_deployment(plan)
    failed = fail_deployment(plan, "timeout")
    deployment = deployment_panel([done, failed])
    assert deployment.status == "degraded", deployment

    registry = incident_registry()
    incident = OperationsIncident(
        incident_id="incident1",
        severity="medium",
        source="deployment",
        status="open",
        summary="deployment issue",
        metadata={"plan_id": plan.plan_id},
    )
    registry = add_incident(registry, incident)
    assert open_incidents(registry) == [incident]

    metrics = operations_metrics([health, runtime, deployment], list(registry.values()))
    assert metrics["panel_count"] == 3, metrics
    assert metrics["degraded_panel_count"] == 1, metrics
    assert metrics["open_incident_count"] == 1, metrics

    print("OPERATIONS CHECK PASSED")


if __name__ == "__main__":
    main()
