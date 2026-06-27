from __future__ import annotations

from typing import Dict, List

from app.platform.registry.registry_models import RegistryResource


def base_registry() -> Dict[str, RegistryResource]:
    resources = [
        RegistryResource(
            resource_id="platform_event_bus",
            resource_type="event_system",
            name="Platform Event Bus",
            source="events",
            metadata={"capability": "event_dispatch"},
        ),
        RegistryResource(
            resource_id="platform_runtime",
            resource_type="runtime_service",
            name="Platform Runtime",
            source="runtime",
            metadata={"capability": "job_execution"},
        ),
        RegistryResource(
            resource_id="platform_plugin_layer",
            resource_type="plugin_system",
            name="Platform Plugin Layer",
            source="plugins",
            metadata={"capability": "provider_extension"},
        ),
    ]
    return {resource.resource_id: resource for resource in resources}


def register_resource(registry: Dict[str, RegistryResource], resource: RegistryResource) -> Dict[str, RegistryResource]:
    updated = dict(registry)
    updated[resource.resource_id] = resource
    return updated


def list_resources(registry: Dict[str, RegistryResource]) -> List[RegistryResource]:
    return list(registry.values())
