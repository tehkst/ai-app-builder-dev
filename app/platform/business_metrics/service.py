from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.database_urls import normalize_sync_database_url
from app.platform.billing.billing_catalog import find_plan
from app.platform.executive_intelligence.evidence_registry import collect_evidence, now_iso

UNKNOWN = "unknown"

_sync_engine = None


def build_business_metrics_summary() -> Dict[str, Any]:
    generated_at = now_iso()
    source = collect_evidence("business_metrics", _collect_business_metrics, generated_at)
    value = source.get("value") or {}
    return {
        "company": "AI Software Factory",
        "product": "Business Metrics",
        "generated_at": generated_at,
        "customers": _claim(value.get("customers"), "organizations", "database_count", generated_at),
        "signups_last_30d": _claim(value.get("signups_last_30d"), "organizations", "database_count", generated_at),
        "team_members": _claim(value.get("team_members"), "users", "database_count", generated_at),
        "mrr_cents": _claim(value.get("mrr_cents"), "organizations.plan", "database_sum", generated_at),
        "source_evidence": source,
    }


def _claim(value: Any, source: str, evidence_type: str, checked_at: str) -> Dict[str, Any]:
    return {
        "status": "observed" if value is not None else UNKNOWN,
        "value": value,
        "source": source,
        "evidence_type": evidence_type,
        "checked_at": checked_at,
        "confidence": "high" if value is not None else "none",
        "unknown_reason": None if value is not None else "The source did not provide this evidence.",
    }


def _get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        from app.core.database import DATABASE_URL

        _sync_engine = create_engine(normalize_sync_database_url(DATABASE_URL), future=True, pool_pre_ping=True)
    return _sync_engine


def _collect_business_metrics() -> Dict[str, Any]:
    from app.models.organization import Organization
    from app.models.user import User

    with Session(_get_sync_engine()) as db:
        customers = db.execute(select(func.count()).select_from(Organization)).scalar_one()
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
        signups_last_30d = db.execute(
            select(func.count()).select_from(Organization).where(Organization.created_at >= cutoff)
        ).scalar_one()
        team_members = db.execute(select(func.count()).select_from(User)).scalar_one()
        plans = db.execute(select(Organization.plan)).scalars().all()

    mrr_cents = 0
    for plan_id in plans:
        try:
            mrr_cents += find_plan(plan_id).monthly_price_cents
        except ValueError:
            continue

    return {
        "customers": customers,
        "signups_last_30d": signups_last_30d,
        "team_members": team_members,
        "mrr_cents": mrr_cents,
    }
