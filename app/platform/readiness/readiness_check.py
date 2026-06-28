from __future__ import annotations

from app.platform.readiness.readiness_flow import run_demo_readiness
from app.platform.readiness.readiness_store import (
    failed_required_items,
    failing_performance,
    passed_required_items,
    passing_performance,
    ready_dependencies,
    ready_environments,
    required_items,
    summarize_readiness,
)


def main() -> None:
    data = run_demo_readiness()
    assert len(data.items) == 4, data
    assert len(data.environments) == 3, data
    assert len(data.dependencies) == 3, data
    assert len(data.performance) == 3, data

    assert len(required_items(data.items)) == 3
    assert len(passed_required_items(data.items)) == 3
    assert len(failed_required_items(data.items)) == 0
    assert len(ready_environments(data.environments)) == 3
    assert len(ready_dependencies(data.dependencies)) == 3
    assert len(passing_performance(data.performance)) == 3
    assert len(failing_performance(data.performance)) == 0

    summary = summarize_readiness(data.items, data.environments, data.dependencies, data.performance)
    assert summary.item_count == 4, summary
    assert summary.passed_required_count == 3, summary
    assert summary.failed_required_count == 0, summary
    assert summary.environment_ready_count == 3, summary
    assert summary.dependency_ready_count == 3, summary
    assert summary.performance_pass_count == 3, summary

    print("READINESS PACK CHECK PASSED")


if __name__ == "__main__":
    main()
