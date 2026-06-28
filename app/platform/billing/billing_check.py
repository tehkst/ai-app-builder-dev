from __future__ import annotations

from app.platform.billing.billing_catalog import billing_plans, find_plan
from app.platform.billing.billing_engine import create_subscription, generate_invoice, record_usage, subscriptions_for_tenant, summarize_billing, usage_for_subscription
from app.platform.billing.billing_workflow import run_demo_billing


def main() -> None:
    plans = billing_plans()
    assert len(plans) == 3, plans
    assert find_plan("growth").included_seats == 10

    subscription = create_subscription("sub1", "org1", "tenant1", "starter", 5)
    assert subscription.status == "active", subscription

    records = [
        record_usage("u1", "sub1", "generation_units", 700, "runtime"),
        record_usage("u2", "sub1", "deployment_units", 600, "deployment"),
    ]
    scoped = usage_for_subscription(records, "sub1")
    assert len(scoped) == 2, scoped

    statement = generate_invoice("statement1", subscription, scoped)
    assert statement.total_cents == 8800, statement
    assert len(statement.lines) == 3, statement.lines

    summary = summarize_billing([subscription], records, [statement])
    assert summary.subscription_count == 1, summary
    assert summary.active_subscription_count == 1, summary
    assert summary.usage_units == 1300, summary
    assert summary.seat_count == 5, summary

    assert subscriptions_for_tenant([subscription], "tenant1") == [subscription]
    assert subscriptions_for_tenant([subscription], "other") == []

    context = run_demo_billing()
    assert len(context.plans) == 3, context
    assert context.subscriptions[0].plan_id == "growth", context.subscriptions[0]
    assert context.invoices[0].total_cents == 26800, context.invoices[0]

    print("SUBSCRIPTION CHECK PASSED")


if __name__ == "__main__":
    main()
