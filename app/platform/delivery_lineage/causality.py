from __future__ import annotations

from typing import Any, Dict, List


def link_causality(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_source = {item["source_record_id"]: item for item in entries}
    last_by_task = {}
    last_by_stage = {}
    last_failure = None
    for item in entries:
        explicit = item.get("caused_by_entry_id")
        if explicit and explicit in by_source:
            item["caused_by_entry_id"] = by_source[explicit]["entry_id"]
            item["causality"] = "proven"
        task_id = item.get("agent_task_id")
        if task_id and task_id in last_by_task and not item.get("parent_entry_id"):
            item["parent_entry_id"] = last_by_task[task_id]["entry_id"]
            item["causality"] = "proven"
        if task_id:
            last_by_task[task_id] = item
        stage = item.get("stage")
        if stage in last_by_stage and not item.get("parent_entry_id"):
            prior = last_by_stage[stage]
            if _same_authority_chain(prior, item):
                item["parent_entry_id"] = prior["entry_id"]
                item["causality"] = "proven"
        last_by_stage[stage] = item
        if item.get("status") in {"failed", "blocked"}:
            last_failure = item
        if _is_repair(item) and last_failure and not item.get("caused_by_entry_id"):
            item["caused_by_entry_id"] = last_failure["entry_id"]
            item["causality"] = "proven"
        item.setdefault("parent_entry_id", None)
        item.setdefault("caused_by_entry_id", None)
        item.setdefault("causality", "unknown")
    return entries


def relationships(entries: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    result = []
    if entries:
        mission = "mission:%s" % entries[0]["mission_id"]
        workflow = "workflow:%s" % entries[0]["workflow_run_id"]
        result.append({"source": mission, "target": workflow, "type": "contains"})
    for item in entries:
        for key, relation in (
            ("parent_entry_id", "follows"),
            ("caused_by_entry_id", "caused_by"),
        ):
            if item.get(key):
                result.append({"source": item["entry_id"], "target": item[key], "type": relation})
        for artifact in item.get("artifact_refs") or []:
            result.append({"source": item["entry_id"], "target": artifact, "type": "produces"})
            for source in item.get("input_artifact_refs") or []:
                result.append({"source": artifact, "target": source, "type": "derives_from"})
        if item.get("agent_task_id"):
            result.append({
                "source": "workflow:%s" % item["workflow_run_id"],
                "target": "agent-task:%s" % item["agent_task_id"],
                "type": "contains",
            })
        for reference in item.get("repository_refs") or []:
            result.append({"source": reference, "target": "mission:%s" % item["mission_id"], "type": "implements"})
        for reference in item.get("deployment_refs") or []:
            result.append({"source": reference, "target": item["entry_id"], "type": "evidences"})
    return result


def _same_authority_chain(prior: Dict[str, Any], current: Dict[str, Any]) -> bool:
    return (
        prior.get("authority") == current.get("authority")
        and prior.get("source_record_id") == current.get("source_record_id")
    )


def _is_repair(item: Dict[str, Any]) -> bool:
    text = "%s %s" % (item.get("event_type"), item.get("stage"))
    return "repair" in text.lower()
