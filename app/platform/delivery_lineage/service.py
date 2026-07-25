from __future__ import annotations

from collections import Counter
from typing import Any, Dict

from app.platform.auth.service import require_founder
from app.platform.delivery_lineage import CONTRACT
from app.platform.delivery_lineage.causality import link_causality, relationships
from app.platform.delivery_lineage.entries import normalize_entries
from app.platform.delivery_lineage.gaps import detect_gaps
from app.platform.delivery_lineage.replay import filter_replay
from app.platform.delivery_lineage.security import sanitize_entries
from app.platform.delivery_lineage.sources import collect_sources


def build_lineage_summary() -> Dict[str, Any]:
    return {
        "contract": CONTRACT, "status": "available", "authority": "projection-only",
        "authenticated_query_required": True,
        "replay_modes": ["chronological", "causal"],
        "mutation_enabled": False,
    }


def build_latest_lineage_summary() -> Dict[str, Any]:
    source = collect_sources()
    if not source.get("found"):
        return {
            "contract": CONTRACT, "status": "no-durable-mission",
            "authority": "projection-only", "mutation_enabled": False,
        }
    projection = _assemble(source, {})
    return {
        "contract": CONTRACT, "status": "ready", "authority": "projection-only",
        "mission_id": projection["mission"]["mission_id"],
        "workflow_run_id": projection["workflow_run"]["workflow_run_id"],
        "current_status": projection["current_status"],
        "entry_count": projection["entry_count"],
        "evidence_completeness": projection["gaps"]["classification"],
        "mutation_enabled": False,
    }


def build_delivery_lineage(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return {
            "status": "unauthorized", "authenticated": False,
            "error": "Founder authentication is required for delivery lineage.",
        }
    source = collect_sources(
        str(payload.get("mission_id") or "").strip(),
        str(payload.get("workflow_run_id") or "").strip(),
    )
    if not source.get("found"):
        return {
            "contract": CONTRACT, "status": "mission-not-found",
            "mission_id": source.get("mission_id"), "workflow_run_id": source.get("workflow_run_id"),
            "entries": [], "gaps": {"classification": "unknown", "items": []},
            "mutation_enabled": False,
        }
    return _assemble(source, payload)


def _assemble(source: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
    entries = sanitize_entries(link_causality(normalize_entries(source)))
    contract = source["state"].get("delivery_contract")
    contract = contract if isinstance(contract, dict) else {}
    replay = filter_replay(entries, filters)
    provider = _provider(source)
    return {
        "contract": CONTRACT, "status": "lineage-ready", "authority": "projection-only",
        "mission": {
            "mission_id": source["mission_id"],
            "title": source["state"].get("title"),
            "founder_objective": contract.get("founder_objective") or source["state"].get("founder_request"),
        },
        "workflow_run": source["run"],
        "current_status": source["state"].get("status") or source["run"].get("status"),
        "current_stage": contract.get("current_stage") or source["state"].get("current_stage"),
        "governance_state": _governance(contract, source),
        "provider_model": provider,
        "entry_count": len(entries), "filtered_entry_count": len(replay),
        "entries": replay, "relationships": relationships(entries),
        "artifact_references": list(contract.get("produced_artifact_references") or []),
        "repository_references": _references(entries, "repository_refs"),
        "deployment_references": _references(entries, "deployment_refs"),
        "production_verification": contract.get("production_verification_reference"),
        "founder_acceptance": contract.get("founder_acceptance"),
        "event_types": dict(Counter(item["event_type"] for item in entries)),
        "gaps": detect_gaps(source, entries),
        "next_action": _next_action(contract, source),
        "mutation_enabled": False, "cache": {"used": False, "authoritative": False},
    }


def _provider(source: Dict[str, Any]) -> Dict[str, Any]:
    context = source["state"].get("context")
    context = context if isinstance(context, dict) else {}
    return {
        "provider": context.get("provider"), "model": context.get("model"),
        "configuration_source": context.get("provider_source") or "mission-context",
        "mission_override": bool(context.get("provider") or context.get("model")),
    }


def _governance(contract: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    action = contract.get("next_governed_action")
    return {
        "approval_state": contract.get("approval_state") or {},
        "current_boundary": action or (contract.get("blockers") or [None])[0],
        "approval_count": len(source["approvals"]),
        "founder_acceptance_distinct_from_deployment": True,
    }


def _references(entries: Any, key: str) -> Any:
    return list(dict.fromkeys(ref for item in entries for ref in item.get(key) or []))


def _next_action(contract: Dict[str, Any], source: Dict[str, Any]) -> Any:
    if contract.get("current_stage") == "complete":
        return None
    return contract.get("next_governed_action") or source["state"].get("next_action") or "Inspect unresolved lineage gaps."
