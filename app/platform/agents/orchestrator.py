from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.platform.services.agent_task_service import create_agent_task
from app.platform.agents.requirements import build_clean_goal, clean_requirements


def build_orchestration_plan(goal: str) -> List[Dict[str, Any]]:
    return [
        {
            "title": "Architecture planning",
            "description": f"Create a technical architecture plan for: {goal}",
            "task_type": "architect_task",
            "priority": "high",
            "risk_level": "medium",
            "approval_required": False,
            "assigned_agent": "architect_agent",
        },
        {
            "title": "Implementation planning",
            "description": f"Prepare implementation steps and files for: {goal}",
            "task_type": "builder_task",
            "priority": "high",
            "risk_level": "high",
            "approval_required": True,
            "assigned_agent": "builder_agent",
        },
        {
            "title": "Code review planning",
            "description": f"Review generated implementation plan for: {goal}",
            "task_type": "reviewer_task",
            "priority": "normal",
            "risk_level": "medium",
            "approval_required": False,
            "assigned_agent": "reviewer_agent",
        },
        {
            "title": "Validation planning",
            "description": f"Prepare tests and validation checks for: {goal}",
            "task_type": "test_task",
            "priority": "normal",
            "risk_level": "low",
            "approval_required": False,
            "assigned_agent": "test_agent",
        },
    ]


def create_child_tasks_for_goal(
    *,
    db: Session,
    parent_task: Dict[str, Any],
) -> Dict[str, Any]:
    input_payload = parent_task.get("input_payload") or {}
    raw_goal = input_payload.get("goal") or parent_task.get("description") or parent_task.get("title")

    requirement_analysis = clean_requirements(str(raw_goal))
    goal = build_clean_goal(requirement_analysis)

    plan = build_orchestration_plan(str(goal))
    child_tasks = []

    for item in plan:
        child = create_agent_task(
            db=db,
            title=item["title"],
            description=item["description"],
            task_type=item["task_type"],
            priority=item["priority"],
            risk_level=item["risk_level"],
            requested_by="orchestrator_agent",
            assigned_agent=item["assigned_agent"],
            input_payload={
                "goal": goal,
                "raw_goal": raw_goal,
                "requirement_analysis": requirement_analysis,
                "parent_task_id": parent_task.get("task_id"),
                "orchestration_role": item["task_type"],
            },
            approval_required=item["approval_required"],
            parent_task_id=parent_task.get("task_id"),
            tenant_id=parent_task.get("tenant_id"),
            workspace_id=parent_task.get("workspace_id"),
            project_id=parent_task.get("project_id"),
        )
        child_tasks.append(child)

    return {
        "success": True,
        "agent_id": "orchestrator_agent",
        "message": "Orchestrator Agent V1 created child task plan.",
        "parent_task_id": parent_task.get("task_id"),
        "goal": goal,
        "raw_goal": raw_goal,
        "requirement_analysis": requirement_analysis,
        "child_task_count": len(child_tasks),
        "child_tasks": child_tasks,
    }
