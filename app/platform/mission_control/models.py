from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CompanyHealth = Literal["healthy", "degraded", "critical"]


@dataclass(frozen=True)
class MissionControlCard:
    title: str
    value: str
    status: CompanyHealth
    description: str


@dataclass(frozen=True)
class MissionControlDepartment:
    name: str
    capability: str
    status: CompanyHealth
    active_work: str


@dataclass(frozen=True)
class CompanyPrinciple:
    category: str
    principle: str
    enforcement: str


@dataclass(frozen=True)
class MissionControlSummary:
    company: str
    product: str
    environment: str
    region: str
    version: str
    health: CompanyHealth
    cards: list[MissionControlCard]
    departments: list[MissionControlDepartment]
    principles: list[CompanyPrinciple]
