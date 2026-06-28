from __future__ import annotations

from app.platform.billing.billing_catalog import billing_plans
from app.platform.billing.billing_engine import create_subscription, generate_invoice, record_usage, usage_for_subscription
from app.platform.billing.billing_models import BillingContext


def run_demo_billing() -> BillingContext:
    subscription = create_subscription(
        "sub_platform",
        "org_platform",
        "tenant_platform",
        "growth",
        12,
    )
    usage_records = [
        record_usage("usage_generation", subscription.subscription_id, "generation_units", 9000, "runtime"),
        record_usage("usage_deployment", subscription.subscription_id, "deployment_units", 2500, "deployment"),
    ]
    invoice = generate_invoice(
        "invoice_platform",
        subscription,
        usage_for_subscription(usage_records, subscription.subscription_id),
    )
    return BillingContext(
        plans=billing_plans(),
        subscriptions=[subscription],
        usage_records=usage_records,
        invoices=[invoice],
        metadata={"workflow": "billing_subscription"},
    )
