from __future__ import annotations

from app.platform.registry.registry import base_registry, list_resources, register_resource
from app.platform.registry.registry_events import resource_registered_event
from app.platform.registry.registry_index import index_by_source, index_by_type
from app.platform.registry.registry_metrics import registry_metrics
from app.platform.registry.registry_models import RegistryResource
from app.platform.registry.registry_query import active_resources, find_resource, resources_by_type
from app.platform.registry.registry_sync import missing_resources, registry_in_sync


def main() -> None:
    registry = base_registry()
    assert find_resource(registry, "platform_runtime") is not None
    assert len(list_resources(registry)) == 3
    assert len(active_resources(registry)) == 3

    runtime_resources = resources_by_type(registry, "runtime_service")
    assert len(runtime_resources) == 1, runtime_resources

    by_type = index_by_type(registry)
    assert "runtime_service" in by_type, by_type

    by_source = index_by_source(registry)
    assert "runtime" in by_source, by_source

    resource = RegistryResource(
        resource_id="platform_learning",
        resource_type="learning_service",
        name="Decision Intelligence",
        source="learning",
        metadata={"capability": "decision_intelligence"},
    )
    registry = register_resource(registry, resource)
    assert find_resource(registry, "platform_learning") == resource

    assert registry_in_sync(registry, ["platform_runtime", "platform_learning"]) is True
    assert missing_resources(registry, ["missing_resource"]) == ["missing_resource"]

    event = resource_registered_event(resource)
    assert event.payload["resource_id"] == "platform_learning", event

    metrics = registry_metrics(registry)
    assert metrics["resource_count"] == 4, metrics
    assert metrics["active_resource_count"] == 4, metrics

    print("REGISTRY CHECK PASSED")


if __name__ == "__main__":
    main()
