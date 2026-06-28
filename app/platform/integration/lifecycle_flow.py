from __future__ import annotations

from typing import Dict

from app.platform.lifecycle.lifecycle_workflow import run_demo_lifecycle
from app.platform.saas_portal.lifecycle_view import portal_lifecycle_plan_view, portal_lifecycle_view
from app.platform.webconsole.lifecycle_view import admin_lifecycle_plan_view, admin_lifecycle_view


def lifecycle_console_portal_flow() -> Dict[str, object]:
    plan = run_demo_lifecycle()

    admin_summary = admin_lifecycle_view([plan.application], plan.events)
    admin_plan = admin_lifecycle_plan_view(plan)

    portal_summary = portal_lifecycle_view(
        [plan.application],
        plan.events,
        plan.application.tenant_id,
    )
    portal_plan = portal_lifecycle_plan_view(plan, plan.application.tenant_id)

    return {
        "application_id": plan.application.application_id,
        "tenant_id": plan.application.tenant_id,
        "final_stage": plan.application.current_stage,
        "admin_card_count": len(admin_summary.cards),
        "admin_stage_count": len(admin_plan.cards),
        "portal_card_count": len(portal_summary.cards),
        "portal_stage_count": len(portal_plan.cards),
        "completed_events": len(plan.events),
    }
