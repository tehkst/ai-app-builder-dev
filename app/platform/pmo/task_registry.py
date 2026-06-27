from __future__ import annotations

from typing import Dict, List, Optional

from app.platform.pmo.planning_models import TaskItem


TASKS: Dict[str, TaskItem] = {
    "implement_constitution_registry": TaskItem(
        task_id="implement_constitution_registry",
        story_id="define_constitution_rules",
        title="Implement constitution registry",
        status="ready",
        owner_agent="backend_builder_agent",
        required_capability="backend_builder_task",
    ),
    "implement_constitution_check": TaskItem(
        task_id="implement_constitution_check",
        story_id="define_constitution_rules",
        title="Implement constitution validation check",
        status="ready",
        owner_agent="test_agent",
        required_capability="test_task",
    ),
}


def all_tasks() -> Dict[str, TaskItem]:
    return dict(TASKS)


def get_task(task_id: str) -> Optional[TaskItem]:
    return TASKS.get(task_id)


def tasks_for_story(story_id: str) -> List[TaskItem]:
    return [task for task in TASKS.values() if task.story_id == story_id]
