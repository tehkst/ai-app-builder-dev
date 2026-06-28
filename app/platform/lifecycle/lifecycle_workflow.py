from __future__ import annotations

from typing import List

from app.platform.lifecycle.lifecycle_catalog import lifecycle_stage_ids
from app.platform.lifecycle.lifecycle_manager import (
    advance_application,
    build_lifecycle_plan,
    create_lifecycle_application,
    record_lifecycle_event,
)
from app.platform.lifecycle.lifecycle_models import LifecycleEvent, LifecyclePlan


def run_demo_lifecycle(
    application_id: str = "life_app_1",
    tenant_id: str = "tenant_platform",
    name: str = "AI CRM App",
    owner: str = "user_platform_owner",
) -> LifecyclePlan:
    application = create_lifecycle_application(application_id, tenant_id, name, owner)
    events: List[LifecycleEvent] = [
        record_lifecycle_event("event_idea", application, owner, "capture_idea")
    ]

    for index, stage_id in enumerate(lifecycle_stage_ids()[1:], start=2):
        application = advance_application(application, stage_id)
        events.append(
            record_lifecycle_event(
                f"event_{stage_id}",
                application,
                owner,
                f"complete_{stage_id}",
                metadata={"sequence": index},
            )
        )

    return build_lifecycle_plan(application, events)
