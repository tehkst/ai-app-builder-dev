from __future__ import annotations

from app.platform.agents.manifest_registry import all_manifests, artifact_owner, find_agents_by_capability


REQUIRED_AGENTS = {
    "architect_agent",
    "backend_builder_agent",
    "database_builder_agent",
    "frontend_builder_agent",
    "reviewer_agent",
    "test_agent",
}

REQUIRED_CAPABILITIES = {
    "architect_task",
    "backend_builder_task",
    "database_builder_task",
    "frontend_builder_task",
    "reviewer_task",
    "test_task",
}

REQUIRED_ARTIFACTS = {
    "generated/backend/service.py",
    "generated/backend/routes.py",
    "generated/backend/models.py",
    "generated/backend/schemas.py",
    "generated/frontend/App.jsx",
}


def main() -> None:
    manifests = all_manifests()
    missing_agents = REQUIRED_AGENTS.difference(manifests)
    assert not missing_agents, sorted(missing_agents)

    for agent_id, manifest in manifests.items():
        assert manifest.agent_id == agent_id, manifest
        assert manifest.department, manifest
        assert manifest.capabilities, manifest
        assert isinstance(manifest.parallelizable, bool), manifest
        assert isinstance(manifest.approval_required, bool), manifest

    for capability in REQUIRED_CAPABILITIES:
        matches = find_agents_by_capability(capability)
        assert matches, capability

    for artifact_path in REQUIRED_ARTIFACTS:
        owner = artifact_owner(artifact_path)
        assert owner is not None, artifact_path

    print("AGENT MANIFEST CHECK PASSED")


if __name__ == "__main__":
    main()
