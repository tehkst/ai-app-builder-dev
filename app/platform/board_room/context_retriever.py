from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Set

from app.platform.board_room.request_decomposer import RequestDecomposer
from app.platform.company_brain.service import build_company_brain_repository_summary
from app.platform.executive_intelligence.service import build_executive_intelligence_briefing
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
        decomposition: Optional[Dict[str, Any]] = None,
        conversation_mode: Optional[str] = None,
        selected_sources: Optional[Set[str]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if lightweight:
            return {
                "founder_request": founder_request,
                "company": "AI Software Factory",
                "sources": {},
                "executive_continuity": {
                    "has_context": False,
                    "mode": "casual-lightweight",
                    "source_failures": [],
                },
            }

        builders = {
            "executive_intelligence": build_executive_intelligence_briefing,
            "company_memory": build_company_brain_repository_summary,
            "mission_history": build_mission_pipeline_summary,
            "repository_intelligence": build_repository_intelligence_summary,
            "engineering_capacity": build_engineering_manager_summary,
        }
        source_names = selected_sources if selected_sources is not None else self._source_names(conversation_mode)
        sources = {name: self._safe(builder) for name, builder in builders.items() if name in source_names}
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
        continuity = self._executive_continuity(sources, founder_request, lifecycle)
        if conversation_mode and conversation_mode not in {
            "status_request", "mission_approval", "execution_command", "implementation_planning"
        }:
            continuity = {
                "has_context": False,
                "mode": "conversation-filtered",
                "source_failures": [],
            }
        return {
            "founder_request": founder_request,
            "company": "AI Software Factory",
            "sources": sources,
            "journey_evidence": journey,
            "evidence_relevance": relevance,
            "lifecycle_context": lifecycle,
            "executive_continuity": continuity,
            "observations": self._observations(sources),
            "source_status": {
                name: str(value.get("status") or "available")
                for name, value in sources.items()
            },
            "conversation_history": self._safe_history(conversation_history or []),
        }

    @staticmethod
    def _safe_history(history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        safe_history = []
        for item in history[-8:]:
            role = str(item.get("role") or item.get("who") or "").lower()
            text = str(item.get("text") or item.get("content") or "").strip()
            if role in {"user", "founder", "assistant", "board", "jarvis"} and text:
                safe_history.append({
                    "role": "founder" if role in {"user", "founder"} else "jarvis",
                    "text": text[:2000],
                })
        return safe_history

    @staticmethod
    def _source_names(conversation_mode: Optional[str]) -> set[str]:
        if not conversation_mode:
            return {
                "executive_intelligence", "company_memory", "mission_history",
                "repository_intelligence", "engineering_capacity",
            }
        if conversation_mode in {"direct_answer", "explanation", "technical_diagnosis", "architecture_review"}:
            return {"executive_intelligence", "repository_intelligence"}
        if conversation_mode == "product_review":
            return {"executive_intelligence", "company_memory", "repository_intelligence"}
        if conversation_mode in {"brainstorming", "executive_discussion", "strategic_advice"}:
            return {"executive_intelligence", "company_memory", "repository_intelligence"}
        if conversation_mode in {"capability_query", "limitation_query"}:
            return set()
        return {
            "executive_intelligence", "company_memory", "mission_history",
            "repository_intelligence", "engineering_capacity",
        }

    @staticmethod
    def _safe(builder: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        try:
            result = builder()
            return result if isinstance(result, dict) else {"status": "unavailable"}
        except Exception as exc:  # Context must never prevent a Board Room response.
            return {"status": "unavailable", "detail": type(exc).__name__}

    @classmethod
    def _executive_continuity(
        cls,
        sources: Dict[str, Dict[str, Any]],
        founder_request: str,
        lifecycle: str,
    ) -> Dict[str, Any]:
        """Build one continuity envelope from capabilities that already exist.

        This intentionally creates no database table, cache, mission registry or
        alternative memory system. It only reconciles the existing Executive
        Intelligence and Mission Pipeline read models for the reasoning layer.
        """

        executive = sources.get("executive_intelligence") or {}
        pipeline = sources.get("mission_history") or {}
        explicit_mission_id = mission_id_from_text(founder_request)
        mission_id = explicit_mission_id or cls._first_value(
            executive,
            ("mission_id", "originating_mission_id", "original_mission_id"),
        )
        if not mission_id:
            mission_id = cls._first_real_pipeline_mission_id(pipeline)

        blocking_reason = cls._first_value(
            executive,
            ("blocking_reason", "blocked_reason", "blocker", "error_classification"),
        )
        workflow_run_id = cls._first_value(
            executive,
            ("workflow_run_id", "run_id"),
        )
        source_failures = [
            name
            for name, value in sources.items()
            if str((value or {}).get("status") or "").lower() in {"unavailable", "unknown", "error", "failed"}
        ]
        pipeline_linked = any(
            not bool(mission.get("synthetic"))
            for mission in (pipeline.get("missions") or [])
            if isinstance(mission, dict)
        )
        has_context = bool(mission_id or workflow_run_id or blocking_reason or pipeline_linked)
        return {
            "has_context": has_context,
            "mode": "existing-capability-reconciliation",
            "mission_id": mission_id,
            "workflow_run_id": workflow_run_id,
            "blocking_reason": blocking_reason,
            "pipeline_linked": pipeline_linked,
            "lifecycle_context": lifecycle,
            "source_failures": source_failures,
            "degraded": bool(source_failures) or (bool(mission_id) and not pipeline_linked),
            "fallback_policy": (
                "continue-with-known-context-and-name-broken-source"
                if has_context
                else "state-that-executive-context-is-unavailable"
            ),
        }

    @classmethod
    def _first_value(cls, payload: Any, keys: tuple[str, ...]) -> str | None:
        if isinstance(payload, dict):
            for key in keys:
                value = payload.get(key)
                if isinstance(value, (str, int)) and str(value).strip():
                    return str(value).strip()
                if isinstance(value, dict):
                    nested = value.get("value")
                    if isinstance(nested, (str, int)) and str(nested).strip():
                        return str(nested).strip()
            for value in payload.values():
                found = cls._first_value(value, keys)
                if found:
                    return found
        elif isinstance(payload, list):
            for value in payload:
                found = cls._first_value(value, keys)
                if found:
                    return found
        return None

    @staticmethod
    def _first_real_pipeline_mission_id(pipeline: Dict[str, Any]) -> str | None:
        for mission in pipeline.get("missions") or []:
            if not isinstance(mission, dict) or mission.get("synthetic"):
                continue
            mission_id = str(mission.get("mission_id") or "").strip()
            if mission_id:
                return mission_id
        return None

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
