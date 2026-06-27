from __future__ import annotations

from typing import Dict


MANAGER_BY_CAPABILITY_PREFIX: Dict[str, str] = {
    "backend": "backend_manager_agent",
    "frontend": "frontend_manager_agent",
    "database": "database_manager_agent",
    "test": "quality_manager_agent",
    "reviewer": "quality_manager_agent",
}


def manager_for_capability(required_capability: str) -> str:
    for prefix, manager_id in MANAGER_BY_CAPABILITY_PREFIX.items():
        if required_capability.startswith(prefix):
            return manager_id
    return "engineering_manager_agent"
