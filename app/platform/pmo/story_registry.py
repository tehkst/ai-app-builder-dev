from __future__ import annotations

from typing import Dict, List, Optional

from app.platform.pmo.planning_models import StoryItem


STORIES: Dict[str, StoryItem] = {
    "define_constitution_rules": StoryItem(
        story_id="define_constitution_rules",
        feature_id="constitution_registry",
        title="Define initial platform constitution rules",
        status="ready",
        priority=1,
        depends_on=[],
    ),
    "define_delegation_rules": StoryItem(
        story_id="define_delegation_rules",
        feature_id="delegation_policy_engine",
        title="Define manager delegation rules",
        status="planned",
        priority=2,
        depends_on=["define_constitution_rules"],
    ),
    "define_sandbox_contract": StoryItem(
        story_id="define_sandbox_contract",
        feature_id="sandbox_executor",
        title="Define controlled runtime sandbox contract",
        status="planned",
        priority=3,
        depends_on=["define_constitution_rules"],
    ),
}


def all_stories() -> Dict[str, StoryItem]:
    return dict(STORIES)


def get_story(story_id: str) -> Optional[StoryItem]:
    return STORIES.get(story_id)


def stories_by_status(status: str) -> List[StoryItem]:
    return [story for story in STORIES.values() if story.status == status]
