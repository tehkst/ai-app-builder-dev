from __future__ import annotations

from app.platform.billing.billing_engine import summarize_billing
from app.platform.billing.billing_models import BillingContext
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def admin_plan_view(context: BillingContext) -> ConsoleView:
    summary = summarize_billing(context.subscriptions, context.usage_records, context.invoices)
    return ConsoleView(
        view_id="admin_plan",
        title="Plans",
        cards=[
            ConsoleCard("plans", "Plans", str(len(context.plans)), "healthy", {}),
            ConsoleCard("subscriptions", "Subscriptions", str(summary.subscription_count), "healthy", {}),
            ConsoleCard("seats", "Seats", str(summary.seat_count), "healthy", {}),
            ConsoleCard("usage", "Usage Units", str(summary.usage_units), "healthy", {}),
        ],
    )
