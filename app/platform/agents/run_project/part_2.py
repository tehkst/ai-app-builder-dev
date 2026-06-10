# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import argparse
from typing import Any, Dict, List, Optional
from app.platform.agents import builtin  # noqa: F401
from app.platform.agents import specialists  # noqa: F401
from app.platform.agents.worker import execute_one_task
from app.platform.persistence.database import PlatformSessionLocal
from app.platform.services.agent_task_service import create_agent_task, list_agent_tasks
SPECIALIST_SEQUENCE = [
    ("architect_agent", "architect_task"),
    ("builder_agent", "builder_task"),
    ("reviewer_agent", "reviewer_task"),
    ("test_agent", "test_task"),
    ("agent_factory_agent", "agent_factory_task"),
]

def continue_project(parent_task_id: str) -> Dict[str, Any]:
    executed_steps: List[Dict[str, Any]] = []

    for agent_id, task_type in SPECIALIST_SEQUENCE:
        result = execute_one_task(
            assigned_agent=agent_id,
            task_type=task_type,
            parent_task_id=parent_task_id,
        )
        executed_steps.append(
            {
                "agent_id": agent_id,
                "task_type": task_type,
                "result": result,
            }
        )

        tasks = get_recent_tasks()
        pending_approvals = _find_pending_approvals(tasks)
        relevant_pending = [
            task for task in pending_approvals
            if task.get("parent_task_id") == parent_task_id
        ]
        if relevant_pending:
            return {
                "success": True,
                "status": "paused_for_approval",
                "message": "Project run is still waiting for approval.",
                "parent_task_id": parent_task_id,
                "pending_approvals": relevant_pending,
                "executed_steps": executed_steps,
            }

    tasks = get_recent_tasks()
    incomplete = _find_incomplete_child_tasks(tasks, parent_task_id)

    return {
        "success": True,
        "status": "completed" if not incomplete else "partially_completed",
        "message": "Project continuation finished.",
        "parent_task_id": parent_task_id,
        "incomplete_child_tasks": incomplete,
        "executed_steps": executed_steps,
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Run a project through AI Software Factory agents.")
    parser.add_argument("--goal", help="Project goal to orchestrate.")
    parser.add_argument("--continue-parent", help="Continue an existing parent task ID after approvals.")
    args = parser.parse_args()

    if not args.goal and not args.continue_parent:
        raise SystemExit("Provide --goal or --continue-parent")

    if args.goal:
        print(run_project_goal(args.goal))
        return

    print(continue_project(args.continue_parent))

if __name__ == "__main__":
    main()
