from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class BillingPlan:
    plan_id: str
    name: str
    monthly_price_cents: int
    included_seats: int
    included_usage_units: int
    overage_unit_price_cents: int
    features: List[str]


@dataclass(frozen=True)
class Subscription:
    subscription_id: str
    organization_id: str
    tenant_id: str
    plan_id: str
    seat_count: int
    status: str


@dataclass(frozen=True)
class UsageRecord:
    usage_id: str
    subscription_id: str
    metric: str
    quantity: int
    source: str


@dataclass(frozen=True)
class InvoiceLine:
    line_id: str
    description: str
    quantity: int
    unit_price_cents: int
    total_cents: int


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    subscription_id: str
    status: str
    currency: str
    lines: List[InvoiceLine]
    total_cents: int


@dataclass(frozen=True)
class BillingSummary:
    subscription_count: int
    active_subscription_count: int
    invoice_count: int
    total_revenue_cents: int
    usage_units: int
    seat_count: int


@dataclass(frozen=True)
class BillingContext:
    plans: List[BillingPlan]
    subscriptions: List[Subscription]
    usage_records: List[UsageRecord]
    invoices: List[Invoice]
    metadata: Dict[str, object]
