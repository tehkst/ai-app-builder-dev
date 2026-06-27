from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class EpicItem:
    epic_id: str
    program_id: str
    title: str
    status: str
    priority: int


@dataclass(frozen=True)
class FeatureItem:
    feature_id: str
    epic_id: str
    title: str
    status: str
    priority: int


@dataclass(frozen=True)
class StoryItem:
    story_id: str
    feature_id: str
    title: str
    status: str
    priority: int
    depends_on: List[str]


@dataclass(frozen=True)
class TaskItem:
    task_id: str
    story_id: str
    title: str
    status: str
    owner_agent: str
    required_capability: str


@dataclass(frozen=True)
class WorkflowItem:
    workflow_id: str
    story_id: str
    name: str
    task_ids: List[str]
    status: str
