"""Customers overview for Mission Control v2 (stage 2).

Joins the customer database (organisations, memberships, users) with both places customer apps
live, the same two sources the Customer Portal's project list merges (`app/api/routes/projects.py`):
- scoped apps (`PlatformScopingRequest`, `request_kind="customer_app"`, `requested_by` = the
  customer's user id), collapsed to the latest version of each amended chain;
- one-shot SaaS-builder apps (`PlatformWorkflowRun` mission runs, `saas_builder.list_builds_by_owner`).
An app only counts as "building" while its workflow is actually running. Read-only, founder
only. If a database can't be read the response says so instead of guessing.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.platform.auth.service import require_founder

CONTRACT = "customers-overview-v1"

ACTIVE_RUN = {"pending", "queued", "running", "approved", "approval_required"}
FAILED_RUN = {"failed", "rejected"}
PUBLISH_STAGE = {"live": "live", "pr_created": "published, PR open", "requested": "waiting to publish",
                 "approved": "waiting to publish", "rejected": "publish declined"}
SAAS_STAGE = {"live": "live", "failed": "build failed", "blocked": "blocked", "cancelled": "cancelled",
              "draft": "scoping", "clarification_required": "scoping", "scope_confirmed": "scoping"}


def app_stage(record: Dict[str, Any], workflow_status: Optional[str] = None) -> str:
    """Where a scoped app stands, in the founder's words. `workflow_status` is the linked run's
    status, or None when there is no run or it could not be found."""
    if record.get("publish_status") in PUBLISH_STAGE:
        return PUBLISH_STAGE[record["publish_status"]]
    if not record.get("workflow_run_id"):
        return "scoping"
    if workflow_status in ACTIVE_RUN:
        return "building"
    if workflow_status == "completed":
        return "built, not published"
    if workflow_status in FAILED_RUN:
        return "build failed"
    return "build status unknown"


def saas_stage(status: Optional[str]) -> str:
    return SAAS_STAGE.get(str(status or "draft"), "building")


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
    from app.platform.saas_builder.service import list_builds_by_owner
    from app.platform.services.scoping_persistence_service import list_scoping_records_for_user
    from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail

    create_platform_tables()
    rows: List[Dict[str, Any]] = []
    with PlatformSessionLocal() as db:
        owners = [o for (o,) in db.query(PlatformScopingRequest.requested_by)
                  .filter(PlatformScopingRequest.request_kind == "customer_app").distinct().all()]
        for owner in owners:
            for record in list_scoping_records_for_user(db, requested_by=owner, limit=10_000):
                if record.get("request_kind") != "customer_app":
                    continue
                run_id = record.get("workflow_run_id")
                detail = get_workflow_run_detail(db, workflow_run_id=run_id) if run_id else {}
                status = detail.get("status") if detail.get("found") else None
                rows.append({"owner": str(owner), **_scoped_view(record, status)})
    for owner, builds in list_builds_by_owner().items():
        rows.extend({"owner": owner, **_saas_view(build)} for build in builds)
    return rows


def _scoped_view(record: Dict[str, Any], workflow_status: Optional[str]) -> Dict[str, Any]:
    return {
        "app_id": record.get("scoping_request_id"),
        "scoping_request_id": record.get("scoping_request_id"),
        "source": "scoping",
        "name": (record.get("normalized_request") or {}).get("app_idea") or "Untitled app",
        "stage": app_stage(record, workflow_status),
        "live_url": record.get("live_url"),
        "pull_request_url": record.get("publish_pull_request_url"),
        "updated_at": record.get("updated_at") or record.get("created_at"),
    }


def _saas_view(build: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "app_id": build.get("workflow_run_id"),
        "scoping_request_id": None,
        "source": "saas_builder",
        "name": build.get("application_name") or "Untitled app",
        "stage": saas_stage(build.get("status")),
        "live_url": build.get("live_url"),
        "pull_request_url": None,
        "updated_at": build.get("updated_at") or build.get("created_at"),
    }


def build_customers_overview(customers: List[Dict[str, Any]], apps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pure join of customers with app views (each carrying its `owner` user id); kept separate so
    the check can exercise it without databases."""
    owner_of = {m["user_id"]: c["organization_id"] for c in customers for m in c["members"]}
    apps_by_org: Dict[str, List[Dict[str, Any]]] = {}
    unmatched = 0
    for app in apps:
        org_id = owner_of.get(str(app.get("owner") or ""))
        if org_id is None:
            unmatched += 1
            continue
        apps_by_org.setdefault(org_id, []).append({k: v for k, v in app.items() if k != "owner"})
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
    building = sum(1 for r in rows for a in r["apps"] if a["stage"] == "building")
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
