from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

MeetingStatus = Literal["scheduled", "in_progress", "completed", "archived"]
DecisionStatus = Literal["draft", "proposed", "approved", "rejected", "superseded"]
ActionStatus = Literal["open", "in_progress", "completed", "blocked"]


@dataclass(frozen=True)
class AgendaItem:
    item_id: str
    title: str
    owner: str
    objective: str


@dataclass(frozen=True)
class BoardDecision:
    decision_id: str
    title: str
    status: DecisionStatus
    owner: str
    summary: str


@dataclass(frozen=True)
class BoardResolution:
    resolution_id: str
    title: str
    status: DecisionStatus
    decision_id: str
    summary: str


@dataclass(frozen=True)
class ActionItem:
    action_id: str
    owner: str
    description: str
    status: ActionStatus


@dataclass(frozen=True)
class BoardMeeting:
    meeting_id: str
    title: str
    status: MeetingStatus
    chair: str
    participants: list[str]
    agenda: list[AgendaItem] = field(default_factory=list)
    decisions: list[BoardDecision] = field(default_factory=list)
    resolutions: list[BoardResolution] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
