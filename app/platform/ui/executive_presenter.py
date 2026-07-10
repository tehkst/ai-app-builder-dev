from __future__ import annotations

from typing import Any


class ExecutivePresenter:
    """Translate Mission Control responses into founder-facing language."""

    STAGE_LABELS = {
        "intent_received": "Planning",
        "requirements_clarified": "Requirements understood",
        "scope_of_work": "Scope defined",
        "architecture_review": "Architecture review",
        "implementation_plan": "Engineering plan ready",
        "validation_plan": "Validation plan ready",
        "founder_approval_required": "Awaiting your approval",
        "ready_for_execution": "Ready to execute",
        "planning": "Planning",
        "engineering": "Engineering",
        "pr": "Pull request review",
        "deploy": "Deployment",
        "verify": "Verification",
        "complete": "Complete",
    }

    def present_mission_created(self, backend_response: dict[str, Any]) -> dict[str, Any]:
        mission = self._mission(backend_response)
        title = self.infer_mission_title(backend_response)
        current_stage = mission.get("current_stage") or mission.get("stage") or mission.get("status")
        return {
            "title": title,
            "mission_id": mission.get("mission_id", "Unknown"),
            "status": self.translate_stage(current_stage),
            "executive_summary": self.build_executive_summary(backend_response),
            "next_action": self.get_next_recommendation(backend_response),
            "visual_progress": self.build_progress_visual(backend_response),
        }

    def translate_stage(self, stage: Any) -> str:
        key = str(stage or "").strip()
        return self.STAGE_LABELS.get(key, self._humanize(key or "in_progress"))

    def infer_mission_title(self, response: dict[str, Any]) -> str:
        mission = self._mission(response)
        title = str(mission.get("title") or mission.get("mission_label") or "").strip()
        if title and not self._is_generic_title(title):
            return title

        request = str(mission.get("founder_request") or response.get("founder_request") or "").strip()
        for line in request.splitlines():
            clean = line.replace("Founder request:", "").strip().strip('"')
            lowered = clean.lower()
            if lowered.startswith(("implement", "improve", "fix", "add", "build", "create", "refine")):
                return clean[:120]

        objective = str(mission.get("objective") or "").strip()
        if objective:
            return objective[:120]
        return "Mission Control improvement"

    def build_executive_summary(self, response: dict[str, Any]) -> str:
        mission = self._mission(response)
        title = self.infer_mission_title(response)
        stage = self.translate_stage(mission.get("current_stage") or mission.get("status"))
        return (
            f"I have prepared an executive mission view for {title}. "
            f"Current status: {stage}. "
            "The next step is gated through the existing Mission Control workflow; no code, merge, "
            "deployment, or rollback action runs from this presentation layer."
        )

    def get_next_recommendation(self, response: dict[str, Any]) -> str:
        mission = self._mission(response)
        for key in ("next_recommended_action", "next_action", "auto_progress_next"):
            value = str(mission.get(key) or "").strip()
            if value:
                return value
        stage = str(mission.get("current_stage") or "").strip()
        if stage == "intent_received":
            return "Generate engineering plan"
        if stage == "founder_approval_required":
            return "Review and approve the engineering plan"
        if stage == "ready_for_execution":
            return "Execute through the approved workflow"
        return "Monitor progress"

    def build_progress_visual(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        mission = self._mission(response)
        stages = mission.get("stages") or mission.get("auto_progress", {}).get("stages") or []
        visual: list[dict[str, Any]] = []
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            name = stage.get("name") or stage.get("stage") or stage.get("label")
            if not name:
                continue
            completed = bool(stage.get("completed") or stage.get("state") == "auto-completed")
            visual.append(
                {
                    "label": self.translate_stage(name),
                    "completed": completed,
                    "icon": "done" if completed else "pending",
                }
            )
        return visual

    def _mission(self, response: dict[str, Any]) -> dict[str, Any]:
        mission = response.get("mission") or response.get("active_mission") or response
        return mission if isinstance(mission, dict) else {}

    def _is_generic_title(self, title: str) -> bool:
        lowered = title.lower()
        return "implementation-request" in lowered or lowered in {"mission", "execution mission"}

    def _humanize(self, value: str) -> str:
        return " ".join(part.capitalize() for part in value.replace("_", " ").replace("-", " ").split())
