from __future__ import annotations

from typing import Any, Dict, List


def filter_replay(entries: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = list(entries)
    stage = str(filters.get("stage") or "").strip()
    agent = str(filters.get("agent") or "").strip()
    evidence_type = str(filters.get("evidence_type") or "").strip()
    mode = str(filters.get("mode") or "chronological").strip().lower()
    if stage:
        result = [item for item in result if item.get("stage") == stage]
    if agent:
        result = [item for item in result if item.get("actor_id") == agent]
    if evidence_type:
        result = [item for item in result if item.get("source_record_type") == evidence_type]
    if filters.get("failures_only"):
        result = [
            item for item in result
            if item.get("status") in {"failed", "blocked"}
            or "repair" in ("%s %s" % (item.get("event_type", ""), item.get("stage", ""))).lower()
        ]
    if filters.get("governance_only"):
        result = [item for item in result if item.get("approval_refs") or item.get("governance_boundary")]
    if filters.get("deployment_only"):
        result = [item for item in result if item.get("stage") in {"repository", "merge", "deployment", "production_verification"}]
    if mode == "causal":
        result.sort(key=lambda item: (_depth(item, entries), item["sequence"]))
    return result


def _depth(item: Dict[str, Any], entries: List[Dict[str, Any]]) -> int:
    by_id = {entry["entry_id"]: entry for entry in entries}
    current, seen, depth = item, set(), 0
    while current.get("caused_by_entry_id") and current["caused_by_entry_id"] not in seen:
        seen.add(current["caused_by_entry_id"])
        current = by_id.get(current["caused_by_entry_id"], {})
        depth += 1
    return depth
