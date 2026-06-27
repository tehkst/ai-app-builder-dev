from __future__ import annotations

from typing import Dict, List

from app.platform.pmo.critical_path import critical_path
from app.platform.pmo.dependency_resolver import blocked_stories, ready_stories
from app.platform.pmo.planning_metrics import planning_metrics


def planning_dashboard() -> Dict[str, object]:
    return {
        "metrics": planning_metrics(),
        "ready_stories": ready_stories(),
        "blocked_stories": blocked_stories(),
        "critical_path": critical_path(),
    }


def dashboard_lines() -> List[str]:
    dashboard = planning_dashboard()
    metrics = dashboard["metrics"]
    return [
        f"stories={metrics['story_count']}",
        f"ready={metrics['ready_story_count']}",
        f"blocked={metrics['blocked_story_count']}",
        "critical_path=" + ">".join(dashboard["critical_path"]),
    ]
