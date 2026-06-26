from __future__ import annotations

from app.platform.engineering.task_graph_runner import run_task_graph_request


def main() -> None:
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
