from __future__ import annotations

from typing import Any, Callable

from app.platform.board_room.request_decomposer import RequestDecomposer
from app.platform.company_brain.service import build_company_brain_repository_summary
from app.platform.company_intelligence.service import build_company_intelligence_snapshot
from app.platform.engineering_manager.service import build_engineering_manager_summary
from app.platform.journey_inspection.service import inspect_mission_journey, mission_id_from_text
from app.platform.pipeline.mission_pipeline import build_mission_pipeline_summary
from app.platform.repository_intelligence.service import build_repository_intelligence_summary


class ContextRetriever:
    """Collects read-only context from existing Mission Control capabilities."""

    def retrieve(
        self,
        founder_request: str,
        *,
        lightweight: bool = False,
        decomposition: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if lightweight:
            return {
                "founder_request": founder_request,
                "company": "AI Software Factory",
                "sources": {},
            }

        sources = {
            "company_intelligence": self._safe(build_company_intelligence_snapshot),
            "company_memory": self._safe(build_company_brain_repository_summary),
            "mission_history": self._safe(build_mission_pipeline_summary),
            "repository_intelligence": self._safe(build_repository_intelligence_summary),
            "engineering_capacity": self._safe(build_engineering_manager_summary),
        }
        decomposition = decomposition or RequestDecomposer().decompose(founder_request)
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
            "observations": self._observations(sources),
            "source_status": {
                name: str(value.get("status") or "available")
                for name, value in sources.items()
            },
        }

    @staticmethod
    def _safe(builder: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        try:
            result = builder()
            return result if isinstance(result, dict) else {"status": "unavailable"}
        except Exception as exc:  # Context must never prevent a Board Room response.
            return {"status": "unavailable", "detail": type(exc).__name__}

    @staticmethod
    def _observations(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
        company = sources.get("company_intelligence") or {}
        pipeline = sources.get("mission_history") or {}
        repository = sources.get("repository_intelligence") or {}
        engineering = sources.get("engineering_capacity") or {}
        journey = sources.get("journey_inspection") or {}
        company_summary = company.get("executive_summary") or {}
        mission_summary = pipeline.get("summary") or {}
        repository_areas = repository.get("repository_areas") or {}
        return {
            "platform_stage": company_summary.get("platform_stage"),
            "estimated_completion_percent": company_summary.get("estimated_completion_percent"),
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
