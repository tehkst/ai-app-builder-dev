from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ManagementRole:
    role_id: str
    title: str
    level: str
    agent_id: str
    delegates_to: List[str]
    responsibilities: List[str]


@dataclass(frozen=True)
class DelegationRule:
    rule_id: str
    from_role_id: str
    to_role_id: str
    capability_area: str
    allowed: bool


MANAGEMENT_LEVELS = {
    "executive",
    "engineering_leadership",
    "department_management",
}
