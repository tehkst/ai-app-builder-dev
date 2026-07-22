from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


SOURCE_ROUTES = {
    "approval": "/admin/approvals",
    "workflow": "/admin/tasks",
    "mission": "/admin/tasks",
    "agent_task": "/admin/agents",
    "incident": "/admin/operations",
    "pull_request": "/admin/releases",
    "deployment": "/admin/deployments",
    "notice": "/admin/notices",
}

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def executive_inbox_view(*, sources: dict[str, Iterable[dict[str, Any]]], now: datetime | None = None) -> ConsoleView:
    """Project existing actionable records into one founder-facing queue.

    The projection is read-only. Source systems remain authoritative for state,
    actions, approvals, missions, workflows, incidents, PRs, and deployments.
    """

    reference_time = now or datetime.now(timezone.utc)
    normalized: dict[str, dict[str, Any]] = {}
    for source_name, records in sources.items():
        for record in records or []:
            if not isinstance(record, dict):
                continue
            item = _normalize(source_name, record, reference_time)
            key = item["authority_reference"]
            previous = normalized.get(key)
            if previous is None or PRIORITY_ORDER[item["priority"]] < PRIORITY_ORDER[previous["priority"]]:
                normalized[key] = item

    items = sorted(
        normalized.values(),
        key=lambda item: (
            PRIORITY_ORDER.get(item["priority"], 99),
            -int(item["age_minutes"]),
            item["authority_reference"],
        ),
    )

    cards = [
        ConsoleCard(
            card_id=f"inbox_{index}_{item['authority_reference']}",
            title=item["title"],
            value=item["action_required"],
            status=item["status"],
            metadata={
                **item,
                "owns_state": False,
                "stores_items": False,
                "action_authority": item["source"],
            },
        )
        for index, item in enumerate(items)
    ]

    if not cards:
        cards = [
            ConsoleCard(
                "executive_inbox_empty",
                "Executive Inbox",
                "No founder action required",
                "healthy",
                {
                    "item_count": 0,
                    "owns_state": False,
                    "stores_items": False,
                    "refresh_behavior": "rebuild-from-existing-sources",
                },
            )
        ]

    return ConsoleView("executive_inbox", "Executive Inbox", cards)


def _normalize(source_name: str, record: dict[str, Any], now: datetime) -> dict[str, Any]:
    source = str(record.get("source") or source_name or "notice").strip().lower()
    authority_reference = _authority_reference(source, record)
    created_at = _parse_time(record.get("created_at") or record.get("updated_at"))
    age_minutes = max(0, int((now - created_at).total_seconds() // 60)) if created_at else 0
    priority = _priority(source, record)
    status = str(record.get("status") or "pending").strip().lower()
    action_required = str(
        record.get("action_required")
        or record.get("next_action")
        or record.get("recommended_action")
        or "Review"
    ).strip()
    title = str(record.get("title") or record.get("subject") or action_required or authority_reference).strip()
    mission_id = _text(record.get("mission_id"))
    workflow_id = _text(record.get("workflow_id") or record.get("workflow_run_id"))
    route = str(record.get("route") or record.get("target") or SOURCE_ROUTES.get(source, "/admin")).strip()
    owner = str(record.get("owner") or record.get("assigned_to") or record.get("agent") or source).strip()
    governance_boundary = str(
        record.get("governance_boundary")
        or record.get("approval_meaning")
        or _default_boundary(source)
    ).strip()

    return {
        "authority_reference": authority_reference,
        "priority": priority,
        "source": source,
        "owner": owner,
        "mission_id": mission_id,
        "workflow_id": workflow_id,
        "title": title,
        "action_required": action_required,
        "status": status,
        "age_minutes": age_minutes,
        "route": route,
        "governance_boundary": governance_boundary,
    }


def _authority_reference(source: str, record: dict[str, Any]) -> str:
    explicit = record.get("authority_reference") or record.get("canonical_reference")
    if explicit:
        return str(explicit)
    for key in (
        "approval_id",
        "workflow_id",
        "workflow_run_id",
        "mission_id",
        "agent_task_id",
        "incident_id",
        "pull_request_id",
        "pr_number",
        "deployment_id",
        "notice_id",
        "id",
    ):
        value = record.get(key)
        if value not in (None, ""):
            return f"{source}:{value}"
    stable = "|".join(
        [
            source,
            str(record.get("title") or record.get("subject") or "item"),
            str(record.get("created_at") or record.get("updated_at") or "unknown"),
        ]
    )
    return stable.lower().replace(" ", "-")


def _priority(source: str, record: dict[str, Any]) -> str:
    explicit = str(record.get("priority") or "").strip().lower()
    if explicit in PRIORITY_ORDER:
        return explicit
    status = str(record.get("status") or "").lower()
    if source == "incident" or status in {"failed", "blocked", "degraded"}:
        return "critical"
    if source in {"approval", "deployment", "pull_request"}:
        return "high"
    if source in {"workflow", "mission", "agent_task"}:
        return "medium"
    return "low"


def _default_boundary(source: str) -> str:
    if source == "approval":
        return "Founder approval must be completed in the existing approval authority."
    if source == "deployment":
        return "Production mutation requires the existing deployment approval gate."
    if source == "pull_request":
        return "Repository merge remains governed by the existing GitHub execution contract."
    if source == "incident":
        return "Incident state and remediation remain owned by the existing operations capability."
    return "The source system remains authoritative; Executive Inbox is read-only."


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value).strip() or None
