from __future__ import annotations

from typing import Any, Dict, List

from app.platform.capability_intelligence.service import discover_relevant_capabilities


CORE_SOURCES = ("executive_intelligence", "mission_history")


class CapabilityRouter:
    """Selects existing platform intelligence before executive reasoning or LLM use."""

    def route(self, founder_request: str, decomposition: Dict[str, Any]) -> Dict[str, Any]:
        objective = str(decomposition.get("primary_objective") or founder_request)
        capability_context = discover_relevant_capabilities(objective, limit=12)
        capabilities = capability_context.get("capabilities") if isinstance(capability_context.get("capabilities"), list) else []
        selected = self._selected_sources(capabilities, decomposition)
        capability_ids = [str(item.get("capability_id")) for item in capabilities if item.get("capability_id")]
        evidence_paths = list(dict.fromkeys(
            str(path)
            for item in capabilities
            for path in item.get("source_paths") or []
            if str(path).strip()
        ))[:12]
        platform_match = bool(capability_ids or selected != list(CORE_SOURCES))
        return {
            "status": "platform-capabilities-selected" if platform_match else "no-platform-capability-proven",
            "request_action": decomposition.get("requested_action"),
            "dominant_goal": decomposition.get("dominant_goal"),
            "primary_capability": selected[0] if selected else "executive_intelligence",
            "secondary_capabilities": selected[1:],
            "fallback_capability": "executive_intelligence",
            "selected_sources": selected,
            "capability_ids": capability_ids,
            "evidence_paths": evidence_paths,
            "capability_context": capability_context,
            "platform_match": platform_match,
            "llm_stage": "last",
        }

    @staticmethod
    def _selected_sources(capabilities: List[Dict[str, Any]], decomposition: Dict[str, Any]) -> List[str]:
        matched_terms = {
            str(term).lower()
            for item in capabilities
            for term in item.get("matched_terms") or []
        }
        evidence_available = bool(capabilities)
        request_type = str(decomposition.get("request_type") or "")
        requested_action = str(decomposition.get("requested_action") or "")
        if request_type == "capability_audit":
            selected = ["capability_intelligence", "repository_intelligence", "architecture_intelligence"]
        elif matched_terms & {"deploy", "deployment", "release", "rollback", "traffic", "verification"}:
            selected = ["deployment", "production_verification"]
        elif matched_terms & {"repository", "health", "readiness", "observability"}:
            selected = ["repository_intelligence"]
        else:
            selected = list(CORE_SOURCES)
        selected.extend(CORE_SOURCES)
        if evidence_available:
            selected.extend(("capability_intelligence", "repository_intelligence"))
        if evidence_available and requested_action in {"ANALYZE", "DIAGNOSE", "QUESTION", "COMPARE", "RECOMMEND"}:
            selected.append("architecture_intelligence")
        if matched_terms & {"deploy", "deployment", "release", "rollback", "traffic", "verification"}:
            selected.extend(("deployment", "production_verification"))
        if matched_terms & {"health", "readiness", "observability"}:
            selected.append("health")
        if matched_terms & {"validation", "acceptance", "governance", "regression"}:
            selected.append("validation")
        if str(decomposition.get("lifecycle_context")) in {"existing_mission_inspection", "mission_continuation"}:
            selected.append("journey_inspection")
        return list(dict.fromkeys(selected))
