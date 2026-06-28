from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ReadinessItem:
    item_id: str
    area: str
    title: str
    status: str
    required: bool


@dataclass(frozen=True)
class EnvironmentCheck:
    check_id: str
    environment: str
    name: str
    status: str


@dataclass(frozen=True)
class DependencyCheck:
    dependency_id: str
    name: str
    version: str
    status: str


@dataclass(frozen=True)
class PerformanceMetric:
    metric_id: str
    name: str
    value: float
    threshold: float
    unit: str


@dataclass(frozen=True)
class ReadinessSummary:
    item_count: int
    passed_required_count: int
    failed_required_count: int
    environment_ready_count: int
    dependency_ready_count: int
    performance_pass_count: int


@dataclass(frozen=True)
class ReadinessContext:
    items: List[ReadinessItem]
    environments: List[EnvironmentCheck]
    dependencies: List[DependencyCheck]
    performance: List[PerformanceMetric]
    metadata: Dict[str, object]
