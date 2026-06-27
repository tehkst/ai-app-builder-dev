from __future__ import annotations

from typing import Dict, List, Optional

from app.platform.registry.registry_models import RegistryResource


def find_resource(registry: Dict[str, RegistryResource], resource_id: str) -> Optional[RegistryResource]:
    return registry.get(resource_id)


def resources_by_type(registry: Dict[str, RegistryResource], resource_type: str) -> List[RegistryResource]:
    return [resource for resource in registry.values() if resource.resource_type == resource_type]


def active_resources(registry: Dict[str, RegistryResource]) -> List[RegistryResource]:
    return [resource for resource in registry.values() if resource.active]
