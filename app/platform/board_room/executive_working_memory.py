from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MISSION_STAGE_ORDER = (
    "planning",
    "engineering",
    "pr",
    "deploy",
    "verify",
    "complete",
)


@dataclass(frozen=True)
class MissionWorkingState:
    mission_id: str | None
    workflow_run_id: str | None
    current_stage: str | None
    next_stage: str | None
    next_action: str | None
    blocking_reason: str | None
    status: str | None
    completed_stages: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "workflow_run_id": self.workflow_run_id,
            "current_stage": self.current_stage,
            "next_stage": self.next_stage,
            "next_action": self.next_action,
            "blocking_reason": self.blocking_reason,
            "status": self.status,
            "completed_stages": list(self.completed_stages),
        }


class ExecutiveWorkingMemory:
    """Builds a deterministic working-memory view from existing mission read models.

    This class does not create a new database, cache, registry, or mission runner. It
    reconciles the existing mission-history and continuity envelopes into a compact
    state object that Jarvis can use for mission continuation.
    """

    @classmethod
    def build(cls, context: dict[str, Any]) -> dict[str, Any]:
        continuity = context.get("executive_continuity") or {}
        sources = context.get("sources") or {}
        pipeline = sources.get("mission_history") or {}
        missions = pipeline.get("missions") or []

        continuity_mission_id = cls._text(continuity.get("mission_id"))
        mission = cls._select_mission(missions, continuity_mission_id)

        mission_id = cls._text(mission.get("mission_id")) or continuity_mission_id
        workflow_run_id = (
            cls._text(mission.get("workflow_run_id"))
            or cls._text(continuity.get("workflow_run_id"))
        )
        status = cls._text(mission.get("status"))
        blocking_reason = (
            cls._text(mission.get("blocking_reason"))
            or cls._text((mission.get("recommendation") or {}).get("blocker"))
            or cls._text(continuity.get("blocking_reason"))
        )

        current_stage = cls._normalize_stage(
            mission.get("current_stage")
            or mission.get("current_autonomous_stage")
            or mission.get("stage")
            or status
        )
        next_action = (
            cls._text(mission.get("next_action"))
            or cls._text((mission.get("recommendation") or {}).get("action"))
            or cls._text(mission.get("auto_progress_next"))
        )
        next_stage = cls._derive_next_stage(current_stage, status, blocking_reason)
        completed_stages = cls._completed_stages(mission, current_stage)

        state = MissionWorkingState(
            mission_id=mission_id,
            workflow_run_id=workflow_run_id,
            current_stage=current_stage,
            next_stage=next_stage,
            next_action=next_action,
            blocking_reason=blocking_reason,
            status=status,
            completed_stages=tuple(completed_stages),
        )
        return {
            "status": "executive-working-memory-ready" if mission_id else "executive-working-memory-unresolved",
            "mode": "existing-read-model-reconciliation",
            "has_active_mission": bool(mission_id and next_stage != "complete"),
            "mission": state.as_dict(),
            "execution_authority": "existing_mission_pipeline",
            "stores_state": False,
            "creates_new_registry": False,
        }

    @staticmethod
    def _select_mission(missions: list[Any], mission_id: str | None) -> dict[str, Any]:
        real = [item for item in missions if isinstance(item, dict) and not item.get("synthetic")]
        if mission_id:
            for mission in real:
                if str(mission.get("mission_id") or "").strip() == mission_id:
                    return mission
        return real[0] if real else {}

    @classmethod
    def _normalize_stage(cls, value: Any) -> str | None:
        text = cls._text(value)
        if not text:
            return None
        normalized = text.lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "planning": "planning",
            "planned": "planning",
            "requirements": "planning",
            "engineering": "engineering",
            "implementation": "engineering",
            "executing": "engineering",
            "change_set_ready": "pr",
            "pull_request": "pr",
            "pr": "pr",
            "review": "pr",
            "merge": "pr",
            "merged": "deploy",
            "deploy": "deploy",
            "deployment": "deploy",
            "deployed": "verify",
            "verify": "verify",
            "verification": "verify",
            "complete": "complete",
            "completed": "complete",
            "done": "complete",
        }
        if normalized in aliases:
            return aliases[normalized]
        for token, stage in aliases.items():
            if token in normalized:
                return stage
        return None

    @staticmethod
    def _derive_next_stage(
        current_stage: str | None,
        status: str | None,
        blocking_reason: str | None,
    ) -> str | None:
        status_text = (status or "").lower()
        blocker_text = (blocking_reason or "").lower()
        if any(token in status_text for token in ("complete", "completed")):
            return "complete"
        if "approval" in blocker_text:
            return current_stage
        if current_stage not in MISSION_STAGE_ORDER:
            return None
        index = MISSION_STAGE_ORDER.index(current_stage)
        return MISSION_STAGE_ORDER[min(index + 1, len(MISSION_STAGE_ORDER) - 1)]

    @classmethod
    def _completed_stages(cls, mission: dict[str, Any], current_stage: str | None) -> list[str]:
        explicit = mission.get("completed_stages")
        if isinstance(explicit, list):
            normalized = [cls._normalize_stage(item) for item in explicit]
            return [item for item in normalized if item]
        if current_stage not in MISSION_STAGE_ORDER:
            return []
        index = MISSION_STAGE_ORDER.index(current_stage)
        return list(MISSION_STAGE_ORDER[:index])

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
