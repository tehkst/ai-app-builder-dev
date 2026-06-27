from __future__ import annotations

from app.platform.delegation.capability_index import agents_for_capability, capability_map
from app.platform.delegation.delegation_engine import delegate
from app.platform.delegation.request_model import DelegationRequest


def main() -> None:
    mapping = capability_map()
    assert "backend_builder_task" in mapping, mapping
    assert "frontend_builder_task" in mapping, mapping
    assert "database_builder_task" in mapping, mapping
    assert agents_for_capability("backend_builder_task"), mapping

    request = DelegationRequest(
        request_id="delegation_check_backend",
        required_capability="backend_builder_task",
        source_story_id="define_constitution_rules",
        priority=1,
    )
    decision = delegate(request)
    assert decision.allowed is True, decision
    assert decision.selected_agent_id == "backend_builder_agent", decision
    assert "backend_builder_agent" in decision.candidate_agent_ids, decision

    missing = delegate(
        DelegationRequest(
            request_id="delegation_check_missing",
            required_capability="missing_capability",
            source_story_id=None,
            priority=9,
        )
    )
    assert missing.allowed is False, missing
    assert missing.selected_agent_id is None, missing

    print("DELEGATION CHECK PASSED")


if __name__ == "__main__":
    main()
