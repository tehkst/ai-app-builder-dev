from __future__ import annotations

from app.platform.agents.manifest_registry import all_manifests, capability_to_agent_map, preferred_agent_id_for_capability, safe_execution_agent_ids
from app.platform.agents.registry import get_agent


REQUIRED_CAPABILITY_ROUTES = {
    "architect_task": "architect_agent",
    "backend_builder_task": "backend_builder_agent",
    "database_builder_task": "database_builder_agent",
    "frontend_builder_task": "frontend_builder_agent",
    "reviewer_task": "reviewer_agent",
    "test_task": "test_agent",
}


def main() -> None:
    manifests = all_manifests()

    for agent_id, manifest in manifests.items():
        registered = get_agent(agent_id)
        assert registered is not None, agent_id
        assert set(manifest.capabilities).issubset(set(registered.capabilities)), {
            "agent_id": agent_id,
            "manifest_capabilities": manifest.capabilities,
            "registered_capabilities": registered.capabilities,
        }
        assert bool(registered.requires_approval_for_new_tasks) == bool(manifest.approval_required), {
            "agent_id": agent_id,
            "manifest_approval_required": manifest.approval_required,
            "registered_requires_approval": registered.requires_approval_for_new_tasks,
        }

    route_map = capability_to_agent_map()
    for capability, agent_id in REQUIRED_CAPABILITY_ROUTES.items():
        assert route_map.get(capability) == agent_id, route_map
        assert preferred_agent_id_for_capability(capability) == agent_id, capability

    safe_ids = set(safe_execution_agent_ids())
    assert set(REQUIRED_CAPABILITY_ROUTES.values()).issubset(safe_ids), safe_ids

    print("AGENT MANIFEST REGISTRY SYNC CHECK PASSED")


if __name__ == "__main__":
    main()
