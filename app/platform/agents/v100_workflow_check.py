from __future__ import annotations

import json
from unittest.mock import patch

from app.platform.engineering.task_graph_runner import run_task_graph_request


_MOCK_GENERATION_OUTPUT = json.dumps(
    {
        "app_name": "Transport Lead CRM",
        "summary": "CRM for tracking transport leads.",
        "files": [
            {"path": "backend/models.py", "language": "python", "purpose": "domain model", "content": "class Lead:\n    pass\n"},
            {"path": "backend/schemas.py", "language": "python", "purpose": "request/response schemas", "content": "class LeadSchema:\n    pass\n"},
            {"path": "backend/routes.py", "language": "python", "purpose": "API routes", "content": "def list_leads():\n    return []\n"},
            {"path": "frontend/App.jsx", "language": "javascript", "purpose": "frontend shell", "content": "export default function App() { return null; }\n"},
            {"path": "README.md", "language": "markdown", "purpose": "readme", "content": "# Transport Lead CRM\n"},
        ],
        "assumptions": [],
        "risks": [],
    }
)


def main() -> None:
    # This check runs in CI without a live AI provider key configured. Mock the
    # generation call (same pattern used elsewhere, e.g. provider_independence_check.py)
    # so the full 7-step task graph is exercised deterministically without network access.
    with patch(
        "app.platform.services.app_generation_service.invoke_ai",
        return_value={"status": "completed", "provider": "mock", "model": "mock", "output_text": _MOCK_GENERATION_OUTPUT},
    ):
        result = run_task_graph_request(
            "Build a simple CRM for transport leads",
            approve_scope=True,
            real_bridge=True,
        )

    summary = result["summary"]
    assert summary["step_count"] == 7, summary
    assert summary["completed_step_count"] == 7, summary
    assert summary["failed_step_count"] == 0, summary
    assert summary["blocked_step_count"] == 0, summary
    assert summary["generated_file_count"] >= 11, summary
    assert summary["materialization_performed"] is False, summary

    expected_agents = {
        "architecture": "architect_agent",
        "backend_contract": "backend_builder_agent",
        "data_model": "database_builder_agent",
        "frontend_shell": "frontend_builder_agent",
        "test_contract": "test_agent",
        "review": "reviewer_agent",
        "release_readiness": "test_agent",
    }

    actual_agents = {
        step["step_id"]: (step.get("selected_agent") or {}).get("agent_id")
        for step in result["execution"]["step_runs"]
    }

    for step_id, expected_agent in expected_agents.items():
        assert actual_agents.get(step_id) == expected_agent, actual_agents

    print("V100 WORKFLOW CHECK PASSED")


if __name__ == "__main__":
    main()
