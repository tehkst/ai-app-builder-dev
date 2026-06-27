from __future__ import annotations

from typing import Dict

from app.platform.pmo.dependency_resolver import blocked_stories, ready_stories
from app.platform.pmo.story_registry import all_stories
from app.platform.pmo.task_registry import all_tasks
from app.platform.pmo.workflow_registry import all_workflows


def planning_metrics() -> Dict[str, int]:
    stories = all_stories()
    return {
        "story_count": len(stories),
        "ready_story_count": len(ready_stories()),
        "blocked_story_count": len(blocked_stories()),
        "task_count": len(all_tasks()),
        "workflow_count": len(all_workflows()),
    }
