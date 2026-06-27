from __future__ import annotations

from app.platform.pmo.critical_path import critical_path
from app.platform.pmo.dependency_resolver import blocked_stories, ready_stories
from app.platform.pmo.planning_dashboard import planning_dashboard
from app.platform.pmo.planning_metrics import planning_metrics


def main() -> None:
    assert "define_constitution_rules" in ready_stories()
    assert "define_delegation_rules" in blocked_stories()
    assert critical_path()
    metrics = planning_metrics()
    assert metrics["story_count"] >= 3
    assert metrics["ready_story_count"] >= 1
    assert metrics["blocked_story_count"] >= 1
    dashboard = planning_dashboard()
    assert dashboard["metrics"]["story_count"] == metrics["story_count"]
    print("PMO GRAPH CHECK PASSED")


if __name__ == "__main__":
    main()
