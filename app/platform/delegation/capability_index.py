from __future__ import annotations

from typing import Dict, List

from app.platform.agents.manifest_registry import all_manifests


def capability_map() -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = {}
    for manifest in all_manifests().values():
        for capability in manifest.capabilities:
            mapping.setdefault(capability, []).append(manifest.agent_id)
    return {key: sorted(value) for key, value in mapping.items()}


def agents_for_capability(capability: str) -> List[str]:
    return capability_map().get(capability, [])
