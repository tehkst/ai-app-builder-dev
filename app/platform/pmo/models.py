from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class PortfolioItem:
    portfolio_id: str
    name: str
    owner: str
    program_ids: List[str]
    status: str


@dataclass(frozen=True)
class ProgramItem:
    program_id: str
    name: str
    owner_department: str
    owner_agent: str
    mission: str
    status: str
    priority: int


@dataclass(frozen=True)
class RoadmapItem:
    roadmap_id: str
    title: str
    phase: str
    status: str
    program_id: str
    sequence: int
    depends_on: List[str]
    completed_in_pr: Optional[str] = None
