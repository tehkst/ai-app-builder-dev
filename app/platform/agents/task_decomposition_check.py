from __future__ import annotations

import argparse
import json

from app.platform.engineering.director import draft_scope_from_request
from app.platform.engineering.task_decomposer import decompose_scope_contract, v99_task_decomposer_status
from app.platform.engineering.task_step_mapper import task_graph_to_steps


def run_task_decomposition_check(request_text: str) -> dict:
    scope_contract = draft_scope_from_request(request_text)
    task_graph = decompose_scope_contract(scope_contract)
    workflow_preview = task_graph_to_steps(task_graph, request_text)
    success = scope_contract.is_valid() and task_graph.get("valid") is True
    return {
        "success": success,
        "version": "v99.2",
        "scope_contract": scope_contract.to_dict(),
        "task_decomposer": v99_task_decomposer_status(),
        "task_graph_generated": True,
        "task_graph": task_graph,
        "workflow_step_preview_generated": True,
        "workflow_step_preview": workflow_preview,
        "workflow_executed": False,
        "reason": "V99.2 generated a task graph and workflow-step preview without executing it.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run V99.2 task decomposition check.")
    parser.add_argument("request_text")
    args = parser.parse_args()
    print(json.dumps(run_task_decomposition_check(args.request_text), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
