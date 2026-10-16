"""Customers overview for Mission Control v2 (stage 2).

Joins the customer database (organisations, memberships, users) with the platform database's
customer-app scoping requests (`request_kind="customer_app"`, `requested_by` = the customer's user
id) so the founder sees each customer, their apps and where each app stands. Read-only, founder
only. If either database can't be read the response says so instead of guessing.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.platform.auth.service import require_founder

CONTRACT = "customers-overview-v1"

# Where an app stands, in the founder's words. Order matters: the first match wins.
STAGES = (
    ("live", lambda r: r.get("publish_status") == "live"),
    ("published, PR open", lambda r: r.get("publish_status") == "pr_created"),
    ("waiting to publish", lambda r: r.get("publish_status") in {"requested", "approved"}),
    ("publish declined", lambda r: r.get("publish_status") == "rejected"),
    ("building", lambda r: bool(r.get("workflow_run_id"))),
    ("scoping", lambda r: True),
)


def app_stage(record: Dict[str, Any]) -> str:
    return next(label for label, matches in STAGES if matches(record))


def _iso(value: Any) -> Optional[str]:
    return value.isoformat() if hasattr(value, "isoformat") else (str(value) if value else None)


def _customer_rows() -> List[Dict[str, Any]]:
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.models.membership import Membership
    from app.models.organization import Organization
    from app.models.user import User
    from app.platform.business_metrics.service import _get_sync_engine

    with Session(_get_sync_engine()) as db:
        orgs = db.execute(select(Organization)).scalars().all()
        members = db.execute(
            select(Membership.organization_id, User.id, User.email).join(User, User.id == Membership.user_id)
        ).all()
    by_org: Dict[str, List[Dict[str, str]]] = {}
    for org_id, user_id, email in members:
        by_org.setdefault(org_id, []).append({"user_id": str(user_id), "email": email})
    return [{
        "organization_id": org.id, "name": org.name, "plan": org.plan, "created_at": _iso(org.created_at),
        "updated_at": _iso(org.updated_at), "members": by_org.get(org.id, []),
    } for org in orgs]


def _app_rows() -> List[Dict[str, Any]]:
    from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
    from app.platform.persistence.model_definitions.scoping import PlatformScopingRequest
    from app.platform.services.scoping_persistence_service import serialize_scoping_record

    create_platform_tables()
    with PlatformSessionLocal() as db:
        records = db.query(PlatformScopingRequest).filter(PlatformScopingRequest.request_kind == "customer_app").all()
        return [serialize_scoping_record(record) for record in records]


def _app_view(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "scoping_request_id": record.get("scoping_request_id"),
        "name": (record.get("normalized_request") or {}).get("app_idea") or "Untitled app",
        "stage": app_stage(record),
        "publish_status": record.get("publish_status"),
        "live_url": record.get("live_url"),
        "pull_request_url": record.get("publish_pull_request_url"),
        "updated_at": record.get("updated_at") or record.get("created_at"),
    }


def build_customers_overview(customers: List[Dict[str, Any]], apps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pure join, kept separate so the check can exercise it without databases."""
    owner_of = {m["user_id"]: c["organization_id"] for c in customers for m in c["members"]}
    apps_by_org: Dict[str, List[Dict[str, Any]]] = {}
    unmatched = 0
    for record in apps:
        org_id = owner_of.get(str(record.get("requested_by") or ""))
        if org_id is None:
            unmatched += 1
            continue
        apps_by_org.setdefault(org_id, []).append(_app_view(record))
    rows = []
    for customer in customers:
        own = sorted(apps_by_org.get(customer["organization_id"], []), key=lambda a: str(a["updated_at"] or ""), reverse=True)
        times = [t for t in [customer["updated_at"], customer["created_at"]] + [a["updated_at"] for a in own] if t]
        rows.append({
            "organization_id": customer["organization_id"], "name": customer["name"], "plan": customer["plan"],
            "created_at": customer["created_at"], "member_count": len(customer["members"]), "apps": own,
            "last_activity": max(times) if times else None,
        })
    rows.sort(key=lambda r: str(r["last_activity"] or ""), reverse=True)
    building = sum(1 for r in rows for a in r["apps"] if a["stage"] in {"building", "scoping"})
    return {"customers": rows, "apps_being_built": building, "apps_without_customer": unmatched}


def list_customers(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not require_founder(payload).get("authorized"):
        return {"contract": CONTRACT, "status": "unauthorized", "authenticated": False}
    try:
        customers = _customer_rows()
    except Exception as exc:  # the customer DB may be absent in some environments
        return {"contract": CONTRACT, "status": "unavailable", "error": "Customer records could not be read: %s" % type(exc).__name__}
    try:
        apps = _app_rows()
    except Exception as exc:
        return {"contract": CONTRACT, "status": "unavailable", "error": "Customer apps could not be read: %s" % type(exc).__name__}
    return {"contract": CONTRACT, "status": "ready", **build_customers_overview(customers, apps)}
