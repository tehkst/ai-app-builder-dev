from __future__ import annotations

import re
from typing import Any


EXECUTION_FIRST_POLICY = """
When a founder-approved mission is active and no governance boundary exists, Jarvis must execute the next workflow stage instead of returning advisory prose.

DO NOT:
- recommend the next step
- provide root-cause analysis instead of acting
- ask whether to continue
- stop after describing an executable action

INSTEAD:
1. Resolve the current mission and workflow stage.
2. Execute the next permitted stage through the existing mission pipeline.
3. Persist the resulting state.
4. Continue until a founder approval boundary, governance restriction, unrecoverable execution error, or mission completion is reached.

An explicit founder authorization in the current request satisfies a pending founder or engineering execution approval gate. Historical read-model blockers must not override the founder's current authorization.

When execution cannot be performed by the current read-only Board Room path, return a structured execution handoff. Never fall back to consultant language.
""".strip()


class ExecutionFirstPolicy:
    """Classifies approved founder commands before recommendation generation.

    This is intentionally policy-only. It does not introduce another mission runner,
    registry, or execution service. The existing mission pipeline remains the single
    execution authority.
    """

    _EXECUTION_COMMAND = re.compile(
        r"^(?:please\s+)?(?:proceed(?:\s+with)?|continue|resume|advance|execute|implement|start|begin|run|ship|deploy|merge|go\s+ahead(?:\s+and)?(?:\s+run)?|approve\s+to\s+proceed|approved\s+to\s+proceed)\b",
        flags=re.IGNORECASE,
    )
    _EXPLICIT_AUTHORIZATION = re.compile(
        r"\b(approved|approve|reviewed|go ahead|proceed|execute|implement|merge|deploy|ship)\b",
        flags=re.IGNORECASE,
    )
    _CONSULTATIVE_REQUEST = re.compile(
        r"\b(what do you recommend|recommendation|advise me|compare options|what should we|should we)\b",
        flags=re.IGNORECASE,
    )

    @classmethod
    def should_execute(
        cls,
        founder_request: str,
        context: dict[str, Any],
        decomposition: dict[str, Any] | None = None,
    ) -> bool:
        normalized = " ".join(founder_request.split())
        if cls._CONSULTATIVE_REQUEST.search(normalized):
            return False
        if not cls.is_execution_instruction(normalized):
            return False

        continuity = context.get("executive_continuity") or {}
        mission_id = str(continuity.get("mission_id") or "").strip()
        lifecycle = str(continuity.get("lifecycle_context") or "").strip().lower()
        workflow_run_id = str(continuity.get("workflow_run_id") or "").strip()

        sources = context.get("sources") or {}
        mission_history = sources.get("mission_history") or {}
        missions = mission_history.get("missions") or []
        eligible = False
        for mission in missions:
            if not isinstance(mission, dict):
                continue
            if mission_id and str(mission.get("mission_id") or "") != mission_id:
                continue
            mission_workflow_run_id = str(mission.get("workflow_run_id") or "").strip()
            if not mission_id or not workflow_run_id or mission_workflow_run_id != workflow_run_id:
                continue
            status_text = " ".join(
                str(mission.get(key) or "")
                for key in (
                    "status",
                    "stage",
                    "approval_status",
                    "blocking_reason",
                    "blocked_reason",
                )
            ).lower()
            terminal = any(token in status_text for token in ("completed", "complete", "rejected", "failed", "orphaned", "unknown", "cancelled"))
            active = any(token in status_text for token in ("approved", "change_set_ready", "execution approval", "running", "active", "accepted", "blocked"))
            if active and not terminal:
                eligible = True
                break

        decomposition = decomposition or {}
        return bool(mission_id and workflow_run_id and eligible and lifecycle in {"mission_continuation", "approved_mission", "decision_support", "governed_execution"})

    @classmethod
    def is_execution_instruction(cls, founder_request: str) -> bool:
        normalized = " ".join(founder_request.strip().split())
        if not normalized or "?" in normalized or cls._CONSULTATIVE_REQUEST.search(normalized):
            return False
        return bool(cls._EXECUTION_COMMAND.search(normalized))

    @classmethod
    def missing_durable_context(cls, decomposition: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        response = "I can continue once you select or create an active mission with a durable workflow run. No eligible mission is currently linked, so I have not executed or changed anything."
        reasoning = {
            "intent": "execution_context_required",
            "presentation_mode": "execution_context_required",
            "request_decomposition": decomposition,
            "execution_handoff": {"state": "mission_selection_required", "mission_id": None, "workflow_run_id": None},
            "governance": {
                "required": str(decomposition.get("requested_action") or "") in {"IMPLEMENT", "GOVERNED_ACTION"},
                "execution_allowed": False,
            },
        }
        return {"reasoning": reasoning, "founder_response": response, "context": context, "technical_details": {"routing": "durable-context-required"}}

    @classmethod
    def handoff(
        cls,
        founder_request: str,
        context: dict[str, Any],
        decomposition: dict[str, Any],
    ) -> dict[str, Any]:
        continuity = context.get("executive_continuity") or {}
        mission_id = str(continuity.get("mission_id") or "").strip() or None
        workflow_run_id = str(continuity.get("workflow_run_id") or "").strip() or None
        blocker = str(continuity.get("blocking_reason") or "").strip() or None
        explicit_authorization = bool(cls._EXPLICIT_AUTHORIZATION.search(founder_request))

        approval_blocker = bool(
            blocker
            and any(
                token in blocker.lower()
                for token in (
                    "approval required",
                    "waiting for founder approval",
                    "waiting for engineering execution approval",
                )
            )
        )
        non_overridable_governance = bool(
            blocker
            and any(
                token in blocker.lower()
                for token in (
                    "policy restriction",
                    "security approval",
                    "compliance approval",
                    "legal approval",
                    "unrecoverable error",
                )
            )
        )
        governance_boundary = non_overridable_governance or (approval_blocker and not explicit_authorization)
        effective_blocker = None if approval_blocker and explicit_authorization else blocker
        state = "blocked" if governance_boundary else "execution_required"
        next_action = (
            "Present the exact founder approval control required to unblock execution."
            if governance_boundary
            else "Dispatch the next executable workflow stage through the existing mission pipeline."
        )

        return {
            "reasoning": {
                "intent": "execute_approved_mission",
                "presentation_mode": "execution_handoff",
                "request_decomposition": {
                    **decomposition,
                    "dominant_goal": "execute_existing_mission",
                },
                "execution_handoff": {
                    "state": state,
                    "mission_id": mission_id,
                    "workflow_run_id": workflow_run_id,
                    "governance_boundary": governance_boundary,
                    "blocking_reason": effective_blocker,
                    "approval_satisfied_by_current_request": approval_blocker and explicit_authorization,
                    "next_action": next_action,
                    "execution_authority": "existing_mission_pipeline",
                    "policy": "execution-first",
                },
                "technical_details": {
                    "routing": "execution-before-recommendation",
                    "read_only_boundary": True,
                    "execution_authority": "existing_mission_pipeline",
                },
            },
            "founder_response": cls._present(
                mission_id=mission_id,
                workflow_run_id=workflow_run_id,
                governance_boundary=governance_boundary,
                blocker=effective_blocker,
                next_action=next_action,
            ),
            "context": context,
            "technical_details": {
                "routing": "execution-before-recommendation",
                "execution_authority": "existing_mission_pipeline",
            },
        }

    @staticmethod
    def _present(
        *,
        mission_id: str | None,
        workflow_run_id: str | None,
        governance_boundary: bool,
        blocker: str | None,
        next_action: str,
    ) -> str:
        lines = [f"I found the active approved mission {mission_id}." if mission_id else "No active mission is linked."]
        if governance_boundary:
            lines.extend(
                [
                    f"It is paused because {blocker or 'founder approval is required.'}",
                    "Use the displayed approval control when you are ready to continue.",
                ]
            )
        else:
            lines.extend(
                [
                    "The next permitted workflow stage is ready to continue through the governed mission pipeline.",
                    f"Workflow run: {workflow_run_id}.",
                ]
            )
        return "\n".join(lines)
