from __future__ import annotations

from typing import Dict, List

from app.platform.registry.registry_models import RegistryResource


def missing_resources(registry: Dict[str, RegistryResource], required_ids: List[str]) -> List[str]:
    return [resource_id for resource_id in required_ids if resource_id not in registry]


def registry_in_sync(registry: Dict[str, RegistryResource], required_ids: List[str]) -> bool:
    return not missing_resources(registry, required_ids)
