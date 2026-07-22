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
        r"\b(proceed|execute|implement|continue|start|begin|run|ship|deploy|merge|go ahead|approve to proceed|approved to proceed)\b",
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
        if not cls._EXECUTION_COMMAND.search(normalized):
            return False

        continuity = context.get("executive_continuity") or {}
        mission_id = str(continuity.get("mission_id") or "").strip()
        lifecycle = str(continuity.get("lifecycle_context") or "").strip().lower()
        has_context = bool(continuity.get("has_context"))

        sources = context.get("sources") or {}
        mission_history = sources.get("mission_history") or {}
        missions = mission_history.get("missions") or []
        approved = False
        for mission in missions:
            if not isinstance(mission, dict):
                continue
            if mission_id and str(mission.get("mission_id") or "") != mission_id:
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
            if any(token in status_text for token in ("approved", "change_set_ready", "execution approval")):
                approved = True
                break

        decomposition = decomposition or {}
        lifecycle_hint = str(decomposition.get("lifecycle_context") or "").lower()
        return bool(
            has_context
            or mission_id
            or approved
            or lifecycle in {"mission_continuation", "approved_mission"}
            or lifecycle_hint in {"mission_continuation", "approved_mission"}
        )

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
        lines = [
            "Execution-first routing",
            f"Mission: {mission_id or 'unresolved'}",
            f"Workflow run: {workflow_run_id or 'unresolved'}",
        ]
        if governance_boundary:
            lines.extend(
                [
                    "Status: PAUSED AT GOVERNANCE BOUNDARY",
                    f"Reason: {blocker or 'Founder approval required.'}",
                    f"Action required: {next_action}",
                ]
            )
        else:
            lines.extend(
                [
                    "Status: EXECUTION REQUIRED",
                    f"Next action: {next_action}",
                    "Jarvis must not replace this action with a recommendation.",
                ]
            )
        return "\n".join(lines)
