from __future__ import annotations

from typing import Iterable

from app.platform.lifecycle.lifecycle_manager import applications_for_tenant, summarize_lifecycle
from app.platform.lifecycle.lifecycle_models import LifecycleApplication, LifecycleEvent, LifecyclePlan
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def portal_lifecycle_view(
    applications: Iterable[LifecycleApplication],
    events: Iterable[LifecycleEvent],
    tenant_id: str,
) -> PortalView:
    scoped_applications = applications_for_tenant(applications, tenant_id)
    scoped_application_ids = {application.application_id for application in scoped_applications}
    scoped_events = [event for event in events if event.application_id in scoped_application_ids]
    summary = summarize_lifecycle(scoped_applications, scoped_events)
    return PortalView(
        view_id="portal_lifecycle",
        title="Application Lifecycle",
        cards=[
            PortalCard("applications", "My Applications", str(summary.application_count), "healthy", {}),
            PortalCard("stages", "Lifecycle Stages", str(summary.stage_count), "healthy", {}),
            PortalCard("events", "Completed Steps", str(summary.completed_stage_count), "healthy", {}),
        ],
    )


def portal_lifecycle_plan_view(plan: LifecyclePlan, tenant_id: str) -> PortalView:
    if plan.application.tenant_id != tenant_id:
        return PortalView("portal_lifecycle_plan", "Application Lifecycle", [])

    return PortalView(
        view_id="portal_lifecycle_plan",
        title=f"Lifecycle: {plan.application.name}",
        cards=[
            PortalCard(
                stage.stage_id,
                stage.title,
                stage.required_artifact,
                "healthy" if stage.sequence <= len(plan.events) else "pending",
                {"sequence": stage.sequence},
            )
            for stage in plan.stages
        ],
    )
