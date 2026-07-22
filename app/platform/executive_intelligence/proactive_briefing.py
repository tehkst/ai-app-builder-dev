from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable


PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
STALE_AFTER_MINUTES = 120


def build_proactive_jarvis_briefing(
    executive_snapshot: dict[str, Any],
    *,
    inbox_sources: dict[str, Iterable[dict[str, Any]]] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a founder-ready briefing from existing authoritative projections.

    This function owns no mission, workflow, approval, inbox, notice, agent-task,
    GitHub, deployment, or verification state. It only composes existing signals.
    """

    reference_time = now or datetime.now(timezone.utc)
    generated_at = str(executive_snapshot.get("generated_at") or reference_time.isoformat())
    signals = _signals_from_snapshot(executive_snapshot, reference_time)
    signals.extend(_signals_from_inbox(inbox_sources or {}, reference_time))
    signals = _dedupe(signals)
    signals.sort(
        key=lambda item: (
            PRIORITY_ORDER.get(item["priority"], 99),
            item["stale"],
            item["authority_reference"],
        )
    )

    critical = [item for item in signals if item["priority"] == "critical"]
    approvals = [item for item in signals if item["category"] == "approval"]
    failed = [item for item in signals if item["category"] in {"workflow", "mission"} and item["status"] in {"failed", "blocked", "degraded"}]
    deployment = [item for item in signals if item["category"] in {"deployment", "verification"}]

    return {
        "company": "AI Software Factory",
        "product": "Proactive Jarvis Briefings",
        "milestone": "AFOS-005",
        "status": "proactive-briefing-ready",
        "generated_at": generated_at,
        "briefing_mode": "on-request-composition",
        "headline": _headline(critical, approvals, signals),
        "summary": {
            "critical_items": len(critical),
            "pending_approvals": len(approvals),
            "failed_or_blocked_workflows": len(failed),
            "deployment_signals": len(deployment),
            "total_signals": len(signals),
            "stale_signals": sum(1 for item in signals if item["stale"]),
        },
        "priorities": signals[:8],
        "blockers": [item for item in signals if item["category"] == "blocker"][:8],
        "pending_approvals": approvals[:8],
        "mission_progress": [item for item in signals if item["category"] == "mission"][:8],
        "failed_workflows": failed[:8],
        "deployment_readiness": deployment[:8],
        "risks": [item for item in signals if item["category"] == "risk"][:8],
        "next_actions": _next_actions(signals),
        "evidence_references": _evidence_references(signals),
        "freshness": {
            "policy": "checked-at-source; stale after 120 minutes unless source says otherwise",
            "stale_after_minutes": STALE_AFTER_MINUTES,
            "generated_at": generated_at,
        },
        "governance": {
            "read_only": True,
            "owns_state": False,
            "stores_briefings": False,
            "scheduler_created": False,
            "source_systems_authoritative": True,
            "founder_approval_boundaries_preserved": True,
            "action_routing": "route-to-existing-source-authority",
        },
    }


def _signals_from_snapshot(snapshot: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for category, key, priority in (
        ("blocker", "blockers", "critical"),
        ("risk", "risks", "high"),
    ):
        for index, item in enumerate(snapshot.get(key) or []):
            signals.append(_normalize_snapshot_item(category, item, index, priority, now))

    mission = snapshot.get("active_mission")
    if isinstance(mission, dict):
        signals.append(_claim_signal("mission", mission, "Active mission", "medium", now))
    stage = snapshot.get("mission_stage")
    if isinstance(stage, dict):
        signals.append(_claim_signal("mission", stage, "Mission stage", "medium", now))

    for category, key, title, priority in (
        ("deployment", "deployed_revision", "Deployed revision", "high"),
        ("deployment", "deployment_traffic", "Deployment traffic", "high"),
        ("verification", "production_verification", "Production verification", "critical"),
        ("workflow", "workflow_status", "Workflow status", "high"),
        ("approval", "next_recommended_action", "Recommended founder action", "high"),
    ):
        value = snapshot.get(key)
        if isinstance(value, dict):
            signals.append(_claim_signal(category, value, title, priority, now))
    return [item for item in signals if item["status"] != "unknown" or item["category"] in {"verification", "deployment"}]


def _signals_from_inbox(sources: dict[str, Iterable[dict[str, Any]]], now: datetime) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for source_name, records in sources.items():
        for record in records or []:
            if not isinstance(record, dict):
                continue
            source = str(record.get("source") or source_name or "notice").lower()
            created_at = _parse_time(record.get("created_at") or record.get("updated_at"))
            checked_at = created_at.isoformat() if created_at else None
            priority = str(record.get("priority") or _priority(source, record)).lower()
            status = str(record.get("status") or "pending").lower()
            reference = str(record.get("authority_reference") or record.get("canonical_reference") or _authority_reference(source, record))
            signals.append(
                {
                    "authority_reference": reference,
                    "category": "approval" if source == "approval" else source,
                    "priority": priority if priority in PRIORITY_ORDER else "low",
                    "title": str(record.get("title") or record.get("subject") or reference),
                    "status": status,
                    "summary": str(record.get("action_required") or record.get("next_action") or record.get("recommended_action") or "Review"),
                    "source": source,
                    "owner": str(record.get("owner") or record.get("agent") or source),
                    "route": str(record.get("route") or record.get("target") or ""),
                    "mission_id": record.get("mission_id"),
                    "workflow_id": record.get("workflow_id") or record.get("workflow_run_id"),
                    "checked_at": checked_at,
                    "freshness": "source-record",
                    "stale": _is_stale(checked_at, now),
                    "governance_boundary": str(record.get("governance_boundary") or "Use the existing source authority for action."),
                }
            )
    return signals


def _normalize_snapshot_item(category: str, item: Any, index: int, priority: str, now: datetime) -> dict[str, Any]:
    if isinstance(item, dict):
        checked_at = item.get("checked_at")
        value = item.get("value") if "value" in item else item
        status = str(item.get("status") or "observed")
        source = str(item.get("source") or category)
        summary = str(value if not isinstance(value, dict) else value.get("message") or value.get("reason") or value)
        title = str(item.get("title") or item.get("name") or category.replace("_", " ").title())
    else:
        checked_at = None
        value = item
        status = "observed"
        source = category
        summary = str(item)
        title = category.replace("_", " ").title()
    return {
        "authority_reference": f"executive-intelligence:{category}:{index}",
        "category": category,
        "priority": priority,
        "title": title,
        "status": status,
        "summary": summary,
        "source": source,
        "owner": source,
        "route": "",
        "mission_id": None,
        "workflow_id": None,
        "checked_at": checked_at,
        "freshness": "checked-on-request",
        "stale": _is_stale(checked_at, now),
        "governance_boundary": "Executive Intelligence is read-only; mutate through the existing source authority.",
    }


def _claim_signal(category: str, claim: dict[str, Any], title: str, priority: str, now: datetime) -> dict[str, Any]:
    value = claim.get("value")
    status = str(claim.get("status") or "unknown")
    checked_at = claim.get("checked_at")
    reference = f"executive-intelligence:{category}:{title.lower().replace(' ', '-')}"
    return {
        "authority_reference": reference,
        "category": category,
        "priority": priority,
        "title": title,
        "status": status,
        "summary": str(value if value is not None else claim.get("unknown_reason") or "No evidence available."),
        "source": str(claim.get("source") or category),
        "owner": str(claim.get("source") or category),
        "route": "",
        "mission_id": None,
        "workflow_id": None,
        "checked_at": checked_at,
        "freshness": str(claim.get("freshness") or "checked-on-request"),
        "stale": _is_stale(checked_at, now),
        "governance_boundary": "Use the existing source authority for any mutation or approval.",
    }


def _dedupe(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for item in signals:
        key = item["authority_reference"]
        current = deduped.get(key)
        if current is None or PRIORITY_ORDER[item["priority"]] < PRIORITY_ORDER[current["priority"]]:
            deduped[key] = item
    return list(deduped.values())


def _next_actions(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions = []
    for item in signals:
        if item["status"] in {"healthy", "completed", "observed"} and item["category"] not in {"approval", "blocker", "risk"}:
            continue
        actions.append(
            {
                "authority_reference": item["authority_reference"],
                "action": item["summary"],
                "route": item["route"],
                "source": item["source"],
                "founder_approval_required": item["category"] in {"approval", "deployment", "verification"},
            }
        )
    return actions[:8]


def _evidence_references(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "authority_reference": item["authority_reference"],
            "source": item["source"],
            "checked_at": item["checked_at"],
            "freshness": item["freshness"],
            "stale": item["stale"],
        }
        for item in signals
    ]


def _headline(critical: list[dict[str, Any]], approvals: list[dict[str, Any]], signals: list[dict[str, Any]]) -> str:
    if critical:
        return f"{len(critical)} critical item(s) require attention."
    if approvals:
        return f"{len(approvals)} founder approval item(s) are pending."
    if signals:
        return "Jarvis has assembled the latest executive operating signals."
    return "No current executive action is required."


def _priority(source: str, record: dict[str, Any]) -> str:
    status = str(record.get("status") or "").lower()
    if source == "incident" or status in {"failed", "blocked", "degraded"}:
        return "critical"
    if source in {"approval", "deployment", "pull_request"}:
        return "high"
    if source in {"workflow", "mission", "agent_task"}:
        return "medium"
    return "low"


def _authority_reference(source: str, record: dict[str, Any]) -> str:
    for key in ("approval_id", "workflow_id", "workflow_run_id", "mission_id", "agent_task_id", "incident_id", "pr_number", "deployment_id", "notice_id", "id"):
        value = record.get(key)
        if value not in (None, ""):
            return f"{source}:{value}"
    return f"{source}:{record.get('title') or record.get('subject') or 'item'}"


def _is_stale(value: Any, now: datetime) -> bool:
    parsed = _parse_time(value)
    if parsed is None:
        return True
    return (now - parsed).total_seconds() > STALE_AFTER_MINUTES * 60


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
