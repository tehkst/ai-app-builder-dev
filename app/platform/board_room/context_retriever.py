from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from app.platform.board_room.request_decomposer import RequestDecomposer
from app.platform.architecture_agent.service import create_architecture_decision
from app.platform.capability_intelligence.service import discover_relevant_capabilities
from app.platform.company_brain.service import build_company_brain_repository_summary
from app.platform.executive_intelligence.service import build_executive_intelligence_briefing
from app.platform.engineering_manager.service import build_engineering_manager_summary
from app.platform.journey_inspection.service import inspect_mission_journey, mission_id_from_text
from app.platform.pipeline.mission_pipeline import build_mission_pipeline_summary
from app.platform.repository_intelligence.service import build_repository_intelligence_summary
from app.platform.repository_intelligence.service import inspect_repository_evidence
from app.platform.deployment.approved_cloud_run import build_cloud_run_deployment_summary
from app.platform.deployment.production_verification import build_production_verification_summary
from app.platform.health.health_status import build_health_status
from app.platform.validation.service import build_validation_summary


class ContextRetriever:
    """Collects read-only context from existing Mission Control capabilities."""

    def retrieve(
        self,
        founder_request: str,
        *,
        lightweight: bool = False,
        decomposition: Optional[Dict[str, Any]] = None,
        capability_route: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if lightweight:
            return {
                "founder_request": founder_request,
                "company": "AI Software Factory",
                "sources": {},
            }

        decomposition = decomposition or RequestDecomposer().decompose(founder_request)
        selected = set((capability_route or {}).get("selected_sources") or ())
        sources = {
            "executive_intelligence": self._safe(build_executive_intelligence_briefing),
            "company_memory": self._safe(build_company_brain_repository_summary),
            "mission_history": self._safe(build_mission_pipeline_summary),
            "engineering_capacity": self._safe(build_engineering_manager_summary),
        }
        capability_context = (capability_route or {}).get("capability_context")
        if "capability_intelligence" in selected:
            sources["capability_intelligence"] = capability_context if isinstance(capability_context, dict) else self._safe(lambda: discover_relevant_capabilities(founder_request))
        if "repository_intelligence" in selected:
            paths = list((capability_route or {}).get("evidence_paths") or ())
            sources["repository_intelligence"] = self._safe(
                lambda: inspect_repository_evidence(paths, requested_by="board-room-capability-router")
            ) if paths else self._safe(build_repository_intelligence_summary)
        if "architecture_intelligence" in selected:
            repository_evidence = sources.get("repository_intelligence") or {}
            sources["architecture_intelligence"] = self._safe(lambda: create_architecture_decision({
                "mission_id": "BOARD-ROOM-READ-ONLY",
                "objective": founder_request,
                "capability_context": sources.get("capability_intelligence") or {},
                "repository_evidence": repository_evidence,
                "existing_constraints": ["Read-only founder analysis. No execution is authorized."],
            }))
        optional_builders = {
            "deployment": build_cloud_run_deployment_summary,
            "production_verification": build_production_verification_summary,
            "health": build_health_status,
            "validation": build_validation_summary,
        }
        for name, builder in optional_builders.items():
            if name in selected:
                sources[name] = self._safe(builder)
        lifecycle = str(decomposition.get("lifecycle_context") or "decision_support")
        journey_applicable = lifecycle in {"existing_mission_inspection", "mission_continuation"}
        journey = inspect_mission_journey(mission_id_from_text(founder_request)) if journey_applicable else {}
        relevance = {
            name: {"applicable": True, "reason": "Provides current read-only operating context."}
            for name in sources
        }
        relevance["journey_inspection"] = {
            "applicable": journey_applicable,
            "reason": (
                "Mission-specific journey evidence is relevant to the requested existing mission."
                if journey_applicable
                else "A new or non-journey request is not expected to have mission-specific journey evidence yet."
            ),
        }
        if journey_applicable:
            sources["journey_inspection"] = journey
        return {
            "founder_request": founder_request,
            "company": "AI Software Factory",
            "sources": sources,
            "journey_evidence": journey,
            "evidence_relevance": relevance,
            "lifecycle_context": lifecycle,
            "capability_route": capability_route or {},
            "observations": self._observations(sources),
            "source_status": {
                name: str(value.get("status") or "available")
                for name, value in sources.items()
            },
        }

    @staticmethod
    def _safe(builder: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        try:
            result = builder()
            return result if isinstance(result, dict) else {"status": "unavailable"}
        except Exception as exc:  # Context must never prevent a Board Room response.
            return {"status": "unavailable", "detail": type(exc).__name__}

    @staticmethod
    def _observations(sources: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        executive = sources.get("executive_intelligence") or {}
        pipeline = sources.get("mission_history") or {}
        repository = sources.get("repository_intelligence") or {}
        engineering = sources.get("engineering_capacity") or {}
        journey = sources.get("journey_inspection") or {}
        mission_summary = pipeline.get("summary") or {}
        repository_areas = repository.get("repository_areas") or {}
        return {
            "platform_stage": (executive.get("mission_stage") or {}).get("value"),
            "project_progress": executive.get("project_progress"),
            "active_missions": mission_summary.get("active", 0),
            "blocked_missions": mission_summary.get("blocked", 0),
            "repository_areas_available": len(repository_areas),
            "engineering_mode": engineering.get("mode"),
            "engineering_requires_founder_approval": bool(
                (engineering.get("governance") or {}).get("founder_approval_required")
            ),
            "pipeline_observer_only": bool(
                (pipeline.get("governance") or {}).get("observer_only")
            ),
            "journey_health": journey.get("journey_health"),
            "journey_verified_stages": journey.get("verified_stage_count", 0),
            "journey_total_stages": journey.get("total_stage_count", 0),
            "journey_verified_transitions": journey.get("verified_transition_count", 0),
            "journey_total_transitions": journey.get("total_transition_count", 0),
            "journey_first_break": journey.get("first_broken_or_manual_transition"),
        }
