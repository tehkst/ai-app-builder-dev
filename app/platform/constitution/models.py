from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ConstitutionRule:
    rule_id: str
    title: str
    category: str
    severity: str
    description: str
    applies_to: List[str]
    blocks_release: bool


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    blocked_by: List[str]
    warnings: List[str]
