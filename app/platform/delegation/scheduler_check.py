from __future__ import annotations

from app.platform.delegation.availability import available_agents
from app.platform.delegation.capability_index import agents_for_capability
from app.platform.delegation.load_tracker import load_for_agent, runtime_profiles
from app.platform.delegation.parallel_scheduler import best_agent_for_request, schedule_requests
from app.platform.delegation.request_model import DelegationRequest


def main() -> None:
    profiles = runtime_profiles()
    assert profiles, "runtime profiles are required"
    assert load_for_agent("missing_agent") == 999

    backend_agents = agents_for_capability("backend_builder_task")
    assert backend_agents, backend_agents
    assert available_agents(backend_agents), backend_agents

    request = DelegationRequest(
        request_id="schedule_backend",
        required_capability="backend_builder_task",
        source_story_id="define_constitution_rules",
        priority=1,
    )
    agent_id = best_agent_for_request(request)
    assert agent_id == "backend_builder_agent", agent_id

    assignments = schedule_requests([request])
    assert assignments["schedule_backend"] == "backend_builder_agent", assignments

    print("DELEGATION SCHEDULER CHECK PASSED")


if __name__ == "__main__":
    main()
