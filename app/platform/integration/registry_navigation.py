from __future__ import annotations

from typing import Dict, List

from app.platform.integration.ui_models import SharedNavigationItem
from app.platform.registry.registry_models import RegistryResource


def navigation_from_registry(registry: Dict[str, RegistryResource], audience: str) -> List[SharedNavigationItem]:
    items: List[SharedNavigationItem] = []
    for resource in registry.values():
        if not resource.active:
            continue
        items.append(
            SharedNavigationItem(
                item_id=f"{audience}_{resource.resource_id}",
                title=resource.name,
                route=f"/{audience}/{resource.resource_type}",
                audience=audience,
                source=resource.source,
            )
        )
    return sorted(items, key=lambda item: item.item_id)


def admin_registry_navigation(registry: Dict[str, RegistryResource]) -> List[SharedNavigationItem]:
    return navigation_from_registry(registry, "admin")


def portal_registry_navigation(registry: Dict[str, RegistryResource]) -> List[SharedNavigationItem]:
    return navigation_from_registry(registry, "portal")
