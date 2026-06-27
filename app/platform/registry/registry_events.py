from __future__ import annotations

from app.platform.events.event import PlatformEvent
from app.platform.events.event_types import VALIDATION_PASSED
from app.platform.registry.registry_models import RegistryResource


def resource_registered_event(resource: RegistryResource) -> PlatformEvent:
    return PlatformEvent(
        event_id=f"registry.{resource.resource_id}.registered",
        event_type=VALIDATION_PASSED,
        source="registry",
        payload={
            "resource_id": resource.resource_id,
            "resource_type": resource.resource_type,
        },
        created_at="registry",
    )
