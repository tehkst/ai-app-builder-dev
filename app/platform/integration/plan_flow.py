from __future__ import annotations

from typing import Dict

from app.platform.billing.billing_workflow import run_demo_billing
from app.platform.saas_portal.plan_view import portal_plan_view
from app.platform.webconsole.plan_view import admin_plan_view


def plan_console_portal_flow() -> Dict[str, object]:
    context = run_demo_billing()
    admin_view = admin_plan_view(context)
    portal_view = portal_plan_view(context, "tenant_platform")
    return {
        "plan_count": len(context.plans),
        "subscription_count": len(context.subscriptions),
        "record_count": len(context.invoices),
        "admin_card_count": len(admin_view.cards),
        "portal_card_count": len(portal_view.cards),
        "tenant_id": context.subscriptions[0].tenant_id,
    }
