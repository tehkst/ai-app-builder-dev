from __future__ import annotations

from typing import Iterable, List

from app.platform.readiness.readiness_models import (
    DependencyCheck,
    EnvironmentCheck,
    PerformanceMetric,
    ReadinessItem,
    ReadinessSummary,
)


def required_items(items: Iterable[ReadinessItem]) -> List[ReadinessItem]:
    return [item for item in items if item.required]


def passed_required_items(items: Iterable[ReadinessItem]) -> List[ReadinessItem]:
    return [item for item in required_items(items) if item.status == "passed"]


def failed_required_items(items: Iterable[ReadinessItem]) -> List[ReadinessItem]:
    return [item for item in required_items(items) if item.status != "passed"]


def ready_environments(checks: Iterable[EnvironmentCheck]) -> List[EnvironmentCheck]:
    return [check for check in checks if check.status == "ready"]


def ready_dependencies(checks: Iterable[DependencyCheck]) -> List[DependencyCheck]:
    return [check for check in checks if check.status == "ready"]


def passing_performance(metrics: Iterable[PerformanceMetric]) -> List[PerformanceMetric]:
    return [metric for metric in metrics if metric.value <= metric.threshold]


def failing_performance(metrics: Iterable[PerformanceMetric]) -> List[PerformanceMetric]:
    return [metric for metric in metrics if metric.value > metric.threshold]


def summarize_readiness(
    items: Iterable[ReadinessItem],
    environments: Iterable[EnvironmentCheck],
    dependencies: Iterable[DependencyCheck],
    performance: Iterable[PerformanceMetric],
) -> ReadinessSummary:
    item_list = list(items)
    return ReadinessSummary(
        item_count=len(item_list),
        passed_required_count=len(passed_required_items(item_list)),
        failed_required_count=len(failed_required_items(item_list)),
        environment_ready_count=len(ready_environments(environments)),
        dependency_ready_count=len(ready_dependencies(dependencies)),
        performance_pass_count=len(passing_performance(performance)),
    )
