"""Recent work on a Codebase Map: what the AI team delivered, shown on the cards it changed.

After each delivered job the map is updated from the delivered code (clients/maps.after_delivery)
and the job becomes a task here: what was asked, the handover summary, how it was delivered, who
approved it, whether it was fully checked, what the AI cost, and each changed file ("new" or
"changed", with its line counts). The newest RECENT_TASKS tasks are kept; a manual update keeps
them too, minus files no longer on the map. Built from records only, with no AI involved.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

RECENT_TASKS = 5
MAX_ITEMS = 40


def task_from_job(*, job: Any, work_item: Any, mission: Any, changed: List[Dict[str, Any]], delivery: Dict[str, Any],
                  previous_files: List[str], cost: Dict[str, Any]) -> Dict[str, Any]:
    handover = getattr(mission, "handover", None) or {}
    old = set(previous_files)
    items = []
    for f in changed[:MAX_ITEMS]:
        lines = "binary file" if f.get("added") is None else f"+{f['added']} −{f['removed']} lines"
        items.append({"ref": f["path"], "change": "changed" if f["path"] in old else "new", "note": lines})
    return {
        "job_id": job.job_id, "work_id": work_item.work_id, "mission_id": work_item.mission_id,
        "title": str(job.title or "")[:120], "request": str(job.notes or job.title or "")[:600],
        "summary": str(handover.get("summary") or getattr(mission, "plan_summary", "") or "")[:1200],
        "changes": [str(c)[:300] for c in (handover.get("changes") or [])[:8]],
        "verified": getattr(mission, "status", "") == "complete",
        "delivery": {k: delivery.get(k) for k in ("kind", "url", "target", "branch", "at")},
        "approved_by": delivery.get("delivered_by") or "",
        "client_agreed": {"by": work_item.consent_by, "provider": work_item.ai_provider, "terms": work_item.consent_terms},
        "cost": {"usd": cost.get("cost_usd"), "calls": cost.get("calls")},
        "items": items, "more_files": max(0, len(changed) - MAX_ITEMS),
    }


def merge(new_task: Optional[Dict[str, Any]], previous: List[Dict[str, Any]], files: List[str]) -> List[Dict[str, Any]]:
    """Newest first, at most RECENT_TASKS, items limited to files on the map; tasks left empty are dropped
    unless they are the new one (a job can change only files the map doesn't show)."""
    on_map = set(files)
    tasks = ([new_task] if new_task else []) + [t for t in previous or [] if not new_task or t.get("work_id") != new_task.get("work_id")]
    out = []
    for i, task in enumerate(tasks[:RECENT_TASKS]):
        items = [it for it in task.get("items") or [] if it.get("ref") in on_map]
        if items or (i == 0 and task is new_task):
            out.append({**task, "items": items})
    return out


def for_client(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The copy sent to the client: no founder email or internal ids."""
    return [{k: v for k, v in t.items() if k not in ("approved_by", "client_agreed", "mission_id", "work_id")}
            for t in tasks]
