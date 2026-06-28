from __future__ import annotations

from typing import Dict, Iterable, List

from app.platform.lifecycle.lifecycle_catalog import lifecycle_stage_ids, lifecycle_stages
from app.platform.lifecycle.lifecycle_models import (
    LifecycleApplication,
    LifecycleEvent,
    LifecyclePlan,
    LifecycleSummary,
)


TERMINAL_STATUSES = {"deployed", "improving", "retired"}


def create_lifecycle_application(
    application_id: str,
    tenant_id: str,
    name: str,
    owner: str,
) -> LifecycleApplication:
    return LifecycleApplication(
        application_id=application_id,
        tenant_id=tenant_id,
        name=name,
        current_stage="idea",
        status="active",
        owner=owner,
    )


def advance_application(
    application: LifecycleApplication,
    target_stage: str,
) -> LifecycleApplication:
    stages = lifecycle_stage_ids()
    if target_stage not in stages:
        raise ValueError(f"Unknown lifecycle stage: {target_stage}")

    current_index = stages.index(application.current_stage)
    target_index = stages.index(target_stage)
    if target_index < current_index:
        raise ValueError("Lifecycle applications cannot move backwards")

    next_status = "active"
    if target_stage == "deployment":
        next_status = "deployed"
    if target_stage == "continuous_improvement":
        next_status = "improving"

    return LifecycleApplication(
        application_id=application.application_id,
        tenant_id=application.tenant_id,
        name=application.name,
        current_stage=target_stage,
        status=next_status,
        owner=application.owner,
    )


def record_lifecycle_event(
    event_id: str,
    application: LifecycleApplication,
    actor: str,
    action: str,
    status: str = "completed",
    metadata: Dict[str, object] | None = None,
) -> LifecycleEvent:
    return LifecycleEvent(
        event_id=event_id,
        application_id=application.application_id,
        stage_id=application.current_stage,
        actor=actor,
        action=action,
        status=status,
        metadata=metadata or {},
    )


def build_lifecycle_plan(
    application: LifecycleApplication,
    events: Iterable[LifecycleEvent],
) -> LifecyclePlan:
    return LifecyclePlan(
        application=application,
        stages=lifecycle_stages(),
        events=list(events),
    )


def summarize_lifecycle(
    applications: Iterable[LifecycleApplication],
    events: Iterable[LifecycleEvent],
) -> LifecycleSummary:
    apps = list(applications)
    event_list = list(events)
    return LifecycleSummary(
        application_count=len(apps),
        active_count=len([app for app in apps if app.status not in TERMINAL_STATUSES]),
        stage_count=len(lifecycle_stages()),
        event_count=len(event_list),
        completed_stage_count=len([event for event in event_list if event.status == "completed"]),
    )


def applications_for_tenant(
    applications: Iterable[LifecycleApplication],
    tenant_id: str,
) -> List[LifecycleApplication]:
    return [application for application in applications if application.tenant_id == tenant_id]
