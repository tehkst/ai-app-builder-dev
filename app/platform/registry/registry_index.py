from __future__ import annotations

from typing import Dict, List

from app.platform.registry.registry_models import RegistryResource


def index_by_type(registry: Dict[str, RegistryResource]) -> Dict[str, List[str]]:
    index: Dict[str, List[str]] = {}
    for resource in registry.values():
        index.setdefault(resource.resource_type, []).append(resource.resource_id)
    return {resource_type: sorted(resource_ids) for resource_type, resource_ids in index.items()}


def index_by_source(registry: Dict[str, RegistryResource]) -> Dict[str, List[str]]:
    index: Dict[str, List[str]] = {}
    for resource in registry.values():
        index.setdefault(resource.source, []).append(resource.resource_id)
    return {source: sorted(resource_ids) for source, resource_ids in index.items()}
