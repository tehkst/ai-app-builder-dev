from __future__ import annotations

from app.platform.billing.billing_engine import subscriptions_for_tenant, summarize_billing
from app.platform.billing.billing_models import BillingContext
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def portal_plan_view(context: BillingContext, tenant_id: str) -> PortalView:
    scoped_subscriptions = subscriptions_for_tenant(context.subscriptions, tenant_id)
    scoped_subscription_ids = {subscription.subscription_id for subscription in scoped_subscriptions}
    scoped_usage = [record for record in context.usage_records if record.subscription_id in scoped_subscription_ids]
    scoped_invoices = [invoice for invoice in context.invoices if invoice.subscription_id in scoped_subscription_ids]
    summary = summarize_billing(scoped_subscriptions, scoped_usage, scoped_invoices)
    return PortalView(
        view_id="portal_plan",
        title="Plan & Usage",
        cards=[
            PortalCard("subscriptions", "Subscriptions", str(summary.subscription_count), "healthy", {}),
            PortalCard("seats", "Seats", str(summary.seat_count), "healthy", {}),
            PortalCard("usage", "Usage Units", str(summary.usage_units), "healthy", {}),
        ],
    )
