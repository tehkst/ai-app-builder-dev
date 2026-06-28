from __future__ import annotations

from app.platform.deployment.deployment_models import DeploymentResult
from app.platform.events.event import PlatformEvent
from app.platform.events.event_types import VALIDATION_PASSED, VALIDATION_FAILED


def deployment_result_event(result: DeploymentResult) -> PlatformEvent:
    event_type = VALIDATION_PASSED if result.status == "completed" else VALIDATION_FAILED
    return PlatformEvent(
        event_id=f"deployment.{result.plan_id}.{result.status}",
        event_type=event_type,
        source="deployment",
        payload={"plan_id": result.plan_id, "status": result.status},
        created_at="deployment",
    )
