from __future__ import annotations

from typing import Iterable

from app.platform.lifecycle.lifecycle_manager import summarize_lifecycle
from app.platform.lifecycle.lifecycle_models import LifecycleApplication, LifecycleEvent, LifecyclePlan
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def admin_lifecycle_view(
    applications: Iterable[LifecycleApplication],
    events: Iterable[LifecycleEvent],
) -> ConsoleView:
    summary = summarize_lifecycle(applications, events)
    return ConsoleView(
        view_id="admin_lifecycle",
        title="AI Application Lifecycle",
        cards=[
            ConsoleCard("applications", "Applications", str(summary.application_count), "healthy", {}),
            ConsoleCard("active", "Active", str(summary.active_count), "healthy", {}),
            ConsoleCard("stages", "Lifecycle Stages", str(summary.stage_count), "healthy", {}),
            ConsoleCard("events", "Lifecycle Events", str(summary.event_count), "healthy", {}),
        ],
    )


def admin_lifecycle_plan_view(plan: LifecyclePlan) -> ConsoleView:
    return ConsoleView(
        view_id="admin_lifecycle_plan",
        title=f"Lifecycle Plan: {plan.application.name}",
        cards=[
            ConsoleCard(
                stage.stage_id,
                stage.title,
                stage.required_artifact,
                "healthy" if stage.sequence <= len(plan.events) else "pending",
                {"owner": stage.service_owner, "sequence": stage.sequence},
            )
            for stage in plan.stages
        ],
    )
