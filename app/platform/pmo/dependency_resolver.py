from __future__ import annotations

from typing import List

from app.platform.pmo.story_registry import all_stories


def blocked_stories() -> List[str]:
    stories = all_stories()
    completed = {story_id for story_id, story in stories.items() if story.status == "completed"}
    blocked: List[str] = []
    for story_id, story in stories.items():
        if story.status == "completed":
            continue
        if any(dependency not in completed for dependency in story.depends_on):
            blocked.append(story_id)
    return sorted(blocked)


def ready_stories() -> List[str]:
    stories = all_stories()
    completed = {story_id for story_id, story in stories.items() if story.status == "completed"}
    ready: List[str] = []
    for story_id, story in stories.items():
        if story.status not in {"ready", "planned"}:
            continue
        if all(dependency in completed for dependency in story.depends_on):
            ready.append(story_id)
    return sorted(ready)
