from __future__ import annotations

from typing import Iterable, List

from app.platform.billing.billing_catalog import find_plan
from app.platform.billing.billing_models import BillingSummary, Invoice, InvoiceLine, Subscription, UsageRecord


ACTIVE_STATUSES = {"active", "trialing"}
SEAT_PRICE_CENTS = 1200


def create_subscription(subscription_id: str, organization_id: str, tenant_id: str, plan_id: str, seat_count: int, status: str = "active") -> Subscription:
    if seat_count < 1:
        raise ValueError("Subscriptions must have at least one seat")
    find_plan(plan_id)
    return Subscription(subscription_id, organization_id, tenant_id, plan_id, seat_count, status)


def record_usage(usage_id: str, subscription_id: str, metric: str, quantity: int, source: str) -> UsageRecord:
    if quantity < 0:
        raise ValueError("Usage quantity cannot be negative")
    return UsageRecord(usage_id, subscription_id, metric, quantity, source)


def usage_for_subscription(usage_records: Iterable[UsageRecord], subscription_id: str) -> List[UsageRecord]:
    return [record for record in usage_records if record.subscription_id == subscription_id]


def subscriptions_for_tenant(subscriptions: Iterable[Subscription], tenant_id: str) -> List[Subscription]:
    return [subscription for subscription in subscriptions if subscription.tenant_id == tenant_id]


def generate_invoice(invoice_id: str, subscription: Subscription, usage_records: Iterable[UsageRecord], currency: str = "USD") -> Invoice:
    plan = find_plan(subscription.plan_id)
    usage_total = sum(record.quantity for record in usage_records)
    usage_extra = max(usage_total - plan.included_usage_units, 0)
    seats_extra = max(subscription.seat_count - plan.included_seats, 0)
    lines = [InvoiceLine("base_plan", plan.name, 1, plan.monthly_price_cents, plan.monthly_price_cents)]
    if seats_extra:
        lines.append(InvoiceLine("seats", "Additional seats", seats_extra, SEAT_PRICE_CENTS, seats_extra * SEAT_PRICE_CENTS))
    if usage_extra:
        lines.append(InvoiceLine("usage", "Additional usage", usage_extra, plan.overage_unit_price_cents, usage_extra * plan.overage_unit_price_cents))
    total = sum(line.total_cents for line in lines)
    return Invoice(invoice_id, subscription.subscription_id, "open", currency, lines, total)


def summarize_billing(subscriptions: Iterable[Subscription], usage_records: Iterable[UsageRecord], invoices: Iterable[Invoice]) -> BillingSummary:
    subscription_list = list(subscriptions)
    usage_list = list(usage_records)
    invoice_list = list(invoices)
    return BillingSummary(
        subscription_count=len(subscription_list),
        active_subscription_count=len([subscription for subscription in subscription_list if subscription.status in ACTIVE_STATUSES]),
        invoice_count=len(invoice_list),
        total_revenue_cents=sum(invoice.total_cents for invoice in invoice_list),
        usage_units=sum(record.quantity for record in usage_list),
        seat_count=sum(subscription.seat_count for subscription in subscription_list),
    )
