from __future__ import annotations

from typing import Any, Callable

from app.platform.company_brain.service import build_company_brain_repository_summary
from app.platform.company_intelligence.service import build_company_intelligence_snapshot
from app.platform.engineering_manager.service import build_engineering_manager_summary
from app.platform.pipeline.mission_pipeline import build_mission_pipeline_summary
from app.platform.repository_intelligence.service import build_repository_intelligence_summary


class ContextRetriever:
    """Collects read-only context from existing Mission Control capabilities."""

    def retrieve(self, founder_request: str, *, lightweight: bool = False) -> dict[str, Any]:
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
        return {
            "founder_request": founder_request,
            "company": "AI Software Factory",
            "sources": sources,
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
        }
