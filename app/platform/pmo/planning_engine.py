from __future__ import annotations

from typing import List, Optional

from app.platform.pmo.planning_models import StoryItem, TaskItem, WorkflowItem
from app.platform.pmo.story_registry import all_stories
from app.platform.pmo.task_registry import tasks_for_story
from app.platform.pmo.workflow_registry import all_workflows


def highest_priority_ready_story() -> Optional[StoryItem]:
    ready = [story for story in all_stories().values() if story.status == "ready"]
    if not ready:
        return None
    return sorted(ready, key=lambda story: story.priority)[0]


def tasks_for_next_story() -> List[TaskItem]:
    story = highest_priority_ready_story()
    if story is None:
        return []
    return tasks_for_story(story.story_id)


def workflow_for_story(story_id: str) -> Optional[WorkflowItem]:
    for workflow in all_workflows().values():
        if workflow.story_id == story_id:
            return workflow
    return None
