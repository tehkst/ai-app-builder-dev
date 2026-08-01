from __future__ import annotations

from unittest.mock import patch

from app.platform.agents.builtin import register_builtin_agents
from app.platform.agents.registry import get_agent
from app.platform.agents.specialists import register_specialist_agents
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.runtime.ai_provider import AIProviderError, AIProviderResult
from app.platform.services.agent_execution_bridge_service import SAFE_EXECUTION_AGENT_ALLOWLIST
from app.platform.services.agent_workflow_executor_service import execute_agent_workflow
from app.platform.services.app_build_workflow_generator_service import generate_app_build_workflow

_MANAGEMENT_AGENT_IDS = [
    "ceo_agent",
    "cto_agent",
    "engineering_manager_agent",
    "backend_manager_agent",
    "frontend_manager_agent",
    "database_manager_agent",
    "quality_manager_agent",
]

_TASK = {"input_payload": {"goal": "Build a booking app for yoga studios", "workflow_context": {}}}


def _result(status: str, output_text: str) -> AIProviderResult:
    return AIProviderResult(status=status, provider="mock", model="mock", output_text=output_text, raw={})


def _check_no_longer_shared_stub() -> None:
    """The bug this whole feature fixes: all 7 roles used to share one handler
    (management_agent_handler) that ignored its skill doc and returned a
    hardcoded {"runtime_execution_changed": False, ...} with no LLM call."""
    handlers = {agent_id: get_agent(agent_id).handler for agent_id in _MANAGEMENT_AGENT_IDS}
    assert len(set(id(handler) for handler in handlers.values())) == len(handlers), handlers
    for agent_id, handler in handlers.items():
        assert handler.__module__ == "app.platform.agents.management_agents.handlers", (agent_id, handler.__module__)
        assert handler.__name__ == f"{agent_id}_handler", (agent_id, handler.__name__)


def _check_allowlisted() -> None:
    for agent_id in _MANAGEMENT_AGENT_IDS:
        assert agent_id in SAFE_EXECUTION_AGENT_ALLOWLIST, agent_id
    # existing code-writing agents must still be present - never loosened by this change
    for agent_id in ("architect_agent", "builder_agent", "reviewer_agent", "test_agent"):
        assert agent_id in SAFE_EXECUTION_AGENT_ALLOWLIST, agent_id


def _check_decision_parsing() -> None:
    from app.platform.agents.management_agents.handlers import cto_agent_handler

    with patch("app.platform.agents.management_agents.core.invoke_provider", return_value=_result("completed", '{"decision": "approve", "rationale": "ok"}')):
        result = cto_agent_handler(_TASK)
        assert result["success"] is True and result["decision"] == "approve", result

    with patch("app.platform.agents.management_agents.core.invoke_provider", return_value=_result("completed", '{"decision": "redirect", "rationale": "needs work", "redirect_instructions": "fix X"}')):
        result = cto_agent_handler(_TASK)
        assert result["success"] is False and result["decision"] == "redirect" and result["redirect_instructions"] == "fix X", result

    with patch("app.platform.agents.management_agents.core.invoke_provider", return_value=_result("completed", "not json at all")):
        result = cto_agent_handler(_TASK)
        assert result["success"] is False and result["decision"] == "escalate", result

    def _raise(*_args, **_kwargs):
        raise AIProviderError("provider unavailable")

    with patch("app.platform.agents.management_agents.core.invoke_provider", side_effect=_raise):
        result = cto_agent_handler(_TASK)
        assert result["success"] is False and result["decision"] == "escalate", result


def _check_workflow_chain_shape() -> None:
    workflow = generate_app_build_workflow(app_request="Build a booking app for yoga studios")
    requires = {step["step_id"]: set(step["requires_steps"]) for step in workflow["steps"]}
    assert requires["ceo_review"] == set(), requires
    assert requires["architecture"] == {"ceo_review"}, requires
    assert requires["engineering_manager_review"] == {"architecture"}, requires
    assert requires["cto_review"] == {"engineering_manager_review"}, requires
    assert requires["builder"] == {"cto_review"}, requires
    for step_id in ("backend_manager_review", "frontend_manager_review", "database_manager_review"):
        assert requires[step_id] == {"builder"}, requires
    assert requires["review"] == {"backend_manager_review", "frontend_manager_review", "database_manager_review"}, requires
    assert requires["quality_manager_review"] == {"review"}, requires
    assert requires["test"] == {"quality_manager_review"}, requires


def _check_rejection_blocks_downstream() -> None:
    """The core Phase 4 requirement: a manager's redirect/escalate decision must
    actually block downstream execution, not just be logged and ignored."""
    db = PlatformSessionLocal()
    try:
        workflow = generate_app_build_workflow(app_request="Build a booking app for yoga studios")
        redirect = _result("completed", '{"decision": "redirect", "rationale": "scope too broad", "redirect_instructions": "narrow it down"}')
        with patch("app.platform.agents.management_agents.core.invoke_provider", return_value=redirect):
            result = execute_agent_workflow(
                db, workflow_name=workflow["workflow_name"], steps=workflow["steps"],
                simulation=False, log_event=False, persist_result=False,
            )
        assert result["status"] == "blocked", result
        assert result["failed_step_count"] == 1, result
        assert result["blocked_step_count"] == len(workflow["steps"]) - 1, result
        statuses = {step["step_id"]: step["status"] for step in result["step_runs"]}
        assert statuses["ceo_review"] == "failed", statuses
        assert statuses["architecture"] == "blocked", statuses
        assert statuses["test"] == "blocked", statuses
    finally:
        db.close()


def main() -> None:
    create_platform_tables()
    register_builtin_agents()
    register_specialist_agents()

    _check_no_longer_shared_stub()
    _check_allowlisted()
    _check_decision_parsing()
    _check_workflow_chain_shape()
    _check_rejection_blocks_downstream()

    print("MANAGEMENT HIERARCHY CHECK PASSED")


if __name__ == "__main__":
    main()
