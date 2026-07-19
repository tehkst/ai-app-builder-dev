from __future__ import annotations

from app.platform.release.release_models import ReleaseContext
from app.platform.release.execution_adapter import execute_release_action


def observe_releases() -> ReleaseContext:
    observed = execute_release_action({"action": "release_history", "actor": "mission_control", "capability": "release_release_history"})
    return ReleaseContext(
        releases=[], versions=[], notes=[], changes=[],
        metadata={"flow": "production_release_adapter", "observed": observed},
    )
