from __future__ import annotations

from typing import List

from app.platform.lifecycle.lifecycle_models import LifecycleStage


LIFECYCLE_STAGE_IDS = [
    "idea",
    "specification",
    "generation",
    "review",
    "version",
    "testing",
    "deployment",
    "monitoring",
    "continuous_improvement",
]


def lifecycle_stages() -> List[LifecycleStage]:
    return [
        LifecycleStage("idea", "Idea", 1, "pmo", "idea_brief"),
        LifecycleStage("specification", "Specification", 2, "pmo", "product_specification"),
        LifecycleStage("generation", "Generation", 3, "runtime", "generated_artifact"),
        LifecycleStage("review", "Review", 4, "engineering_management", "review_record"),
        LifecycleStage("version", "Version", 5, "artifact_registry", "version_record"),
        LifecycleStage("testing", "Testing", 6, "runtime_engine", "test_report"),
        LifecycleStage("deployment", "Deployment", 7, "deployment_platform", "deployment_plan"),
        LifecycleStage("monitoring", "Monitoring", 8, "operations_center", "health_snapshot"),
        LifecycleStage(
            "continuous_improvement",
            "Continuous Improvement",
            9,
            "decision_intelligence",
            "improvement_backlog",
        ),
    ]


def lifecycle_stage_ids() -> List[str]:
    return [stage.stage_id for stage in lifecycle_stages()]
