from __future__ import annotations

from app.platform.delegation.approval_gate import approval_required, approval_status
from app.platform.delegation.assignment_strategy import first_available, least_loaded
from app.platform.delegation.delegation_audit import audit_decision
from app.platform.delegation.delegation_engine import delegate
from app.platform.delegation.escalation_engine import escalation_target, requires_escalation
from app.platform.delegation.manager_router import manager_for_capability
from app.platform.delegation.request_model import DelegationRequest


def main() -> None:
    assert manager_for_capability("backend_builder_task") == "backend_manager_agent"
    assert manager_for_capability("frontend_builder_task") == "frontend_manager_agent"
    assert manager_for_capability("unknown_task") == "engineering_manager_agent"

    assert requires_escalation("backend_builder_task", 0) is True
    assert escalation_target("backend_builder_task", 0) == "backend_manager_agent"
    assert escalation_target("backend_builder_task", 1) == ""

    assert approval_required("deployment") is True
    assert approval_status("deployment") == "required"
    assert approval_status("deployment", approved=True) == "approved"

    assert first_available(["b", "a"]) == "a"
    assert least_loaded(["backend_builder_agent"]) == "backend_builder_agent"

    request = DelegationRequest(
        request_id="manager_check_backend",
        required_capability="backend_builder_task",
        source_story_id="define_constitution_rules",
        priority=1,
    )
    decision = delegate(request)
    record = audit_decision(decision, manager_for_capability(request.required_capability))
    assert record["manager_id"] == "backend_manager_agent", record
    assert record["selected_agent_id"] == "backend_builder_agent", record

    print("DELEGATION MANAGER CHECK PASSED")


if __name__ == "__main__":
    main()
