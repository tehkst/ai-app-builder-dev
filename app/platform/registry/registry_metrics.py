from __future__ import annotations

from typing import Dict

from app.platform.registry.registry_models import RegistryResource


def registry_metrics(registry: Dict[str, RegistryResource]) -> Dict[str, int]:
    active_count = len([resource for resource in registry.values() if resource.active])
    type_count = len({resource.resource_type for resource in registry.values()})
    source_count = len({resource.source for resource in registry.values()})
    return {
        "resource_count": len(registry),
        "active_resource_count": active_count,
        "resource_type_count": type_count,
        "source_count": source_count,
    }
