from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class OnboardingStep:
    step_id: str
    tenant_id: str
    title: str
    category: str
    status: str
    order: int


@dataclass(frozen=True)
class OnboardingGuide:
    guide_id: str
    tenant_id: str
    title: str
    audience: str
    status: str


@dataclass(frozen=True)
class OnboardingSummary:
    guide_count: int
    step_count: int
    done_count: int
    open_count: int
    progress_percent: int


@dataclass(frozen=True)
class OnboardingContext:
    guides: List[OnboardingGuide]
    steps: List[OnboardingStep]
    metadata: Dict[str, object]
