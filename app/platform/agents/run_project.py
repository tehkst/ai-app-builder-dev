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


def _find_pending_approvals(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        task
        for task in tasks
        if task.get("status") == "approval_required" and task.get("approval_id")
    ]


def _find_incomplete_child_tasks(
    tasks: List[Dict[str, Any]],
    parent_task_id: str,
) -> List[Dict[str, Any]]:
    return [
        task
        for task in tasks
        if task.get("parent_task_id") == parent_task_id
        and task.get("status") not in {"completed", "cancelled", "failed"}
    ]


def create_project_orchestrator_task(goal: str) -> Dict[str, Any]:
    db = PlatformSessionLocal()
    try:
        return create_agent_task(
            db=db,
            title=f"Project orchestration: {goal[:80]}",
            description="Run Orchestrator Agent V1 for a user project goal.",
            task_type="orchestrator_task",
            priority="urgent",
            risk_level="medium",
            requested_by="platform_admin",
            assigned_agent="orchestrator_agent",
            input_payload={
                "goal": goal,
            },
            approval_required=False,
        )
    finally:
        db.close()


def get_recent_tasks(limit: int = 100) -> List[Dict[str, Any]]:
    db = PlatformSessionLocal()
    try:
        return list_agent_tasks(db=db, limit=limit)
    finally:
        db.close()


def run_project_goal(goal: str) -> Dict[str, Any]:
    parent_task = create_project_orchestrator_task(goal)
    parent_task_id = parent_task["task_id"]

    orchestration_result = execute_one_task(
        assigned_agent="orchestrator_agent",
        task_type="orchestrator_task",
    )

    tasks = get_recent_tasks()
    pending_approvals = [
        task for task in _find_pending_approvals(tasks)
        if task.get("parent_task_id") == parent_task_id
    ]

    executed_steps: List[Dict[str, Any]] = [
        {
            "agent_id": "orchestrator_agent",
            "task_type": "orchestrator_task",
            "result": orchestration_result,
        }
    ]

    if pending_approvals:
        return {
            "success": True,
            "status": "paused_for_approval",
            "message": "Project run paused because approval is required.",
            "parent_task_id": parent_task_id,
            "pending_approvals": pending_approvals,
            "executed_steps": executed_steps,
        }

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
        pending_approvals = [
            task for task in _find_pending_approvals(tasks)
            if task.get("parent_task_id") == parent_task_id
        ]
        if pending_approvals:
            return {
                "success": True,
                "status": "paused_for_approval",
                "message": "Project run paused because approval is required.",
                "parent_task_id": parent_task_id,
                "pending_approvals": pending_approvals,
                "executed_steps": executed_steps,
            }

    tasks = get_recent_tasks()
    incomplete = _find_incomplete_child_tasks(tasks, parent_task_id)

    return {
        "success": True,
        "status": "completed" if not incomplete else "partially_completed",
        "message": "Project run finished.",
        "parent_task_id": parent_task_id,
        "incomplete_child_tasks": incomplete,
        "executed_steps": executed_steps,
    }


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
