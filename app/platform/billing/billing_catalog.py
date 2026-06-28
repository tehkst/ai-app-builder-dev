from __future__ import annotations

from typing import List

from app.platform.billing.billing_models import BillingPlan


def billing_plans() -> List[BillingPlan]:
    return [
        BillingPlan(
            plan_id="starter",
            name="Starter",
            monthly_price_cents=4900,
            included_seats=3,
            included_usage_units=1000,
            overage_unit_price_cents=5,
            features=["projects", "generation", "basic_support"],
        ),
        BillingPlan(
            plan_id="growth",
            name="Growth",
            monthly_price_cents=19900,
            included_seats=10,
            included_usage_units=10000,
            overage_unit_price_cents=3,
            features=["projects", "generation", "deployment", "team_workspace"],
        ),
        BillingPlan(
            plan_id="enterprise",
            name="Enterprise",
            monthly_price_cents=79900,
            included_seats=50,
            included_usage_units=100000,
            overage_unit_price_cents=1,
            features=["governance", "sso", "audit", "premium_support"],
        ),
    ]


def find_plan(plan_id: str) -> BillingPlan:
    for plan in billing_plans():
        if plan.plan_id == plan_id:
            return plan
    raise ValueError(f"Unknown billing plan: {plan_id}")
