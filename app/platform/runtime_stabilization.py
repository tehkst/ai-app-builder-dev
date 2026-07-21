from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.platform.engineering.change_set_service import generate_executable_change_set
from app.platform.execution.service import (
    get_execution_mission_evidence,
    record_execution_mission_evidence,
)


RUNTIME_STABILIZATION_VERSION = "MC-RUNTIME-01"


@dataclass(frozen=True)
class RuntimeStabilizationResult:
    mission_id: str
    status: str
    change_set_status: str
    attempted: bool
    retryable: bool
    blocked_reason: str | None
    remaining_failed_checks: tuple[dict[str, Any], ...]
    next_action: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "milestone": RUNTIME_STABILIZATION_VERSION,
            "mission_id": self.mission_id,
            "status": self.status,
            "change_set_status": self.change_set_status,
            "attempted": self.attempted,
            "retryable": self.retryable,
            "blocked_reason": self.blocked_reason,
            "remaining_failed_checks": list(self.remaining_failed_checks),
            "next_action": self.next_action,
        }


def stabilize_mission_runtime(
    mission_id: str,
    *,
    provider: str | None = None,
    model: str | None = None,
    progress_observer: Callable[..., None] | None = None,
) -> RuntimeStabilizationResult:
    """Reconcile one blocked mission through existing authoritative services.

    MC-RUNTIME-01 intentionally owns no reasoning, planning, validation,
    execution, learning, or digital-twin logic. It coordinates the existing
    mission evidence store and executable change-set service so a blocked
    mission can be retried deterministically without creating a parallel
    runtime architecture.
    """

    normalized = str(mission_id or "").strip()
    if not normalized:
        raise ValueError("mission_id is required")

    mission = get_execution_mission_evidence(normalized) or {}
    if mission.get("mission_id") != normalized:
        return RuntimeStabilizationResult(
            mission_id=normalized,
            status="blocked",
            change_set_status="blocked",
            attempted=False,
            retryable=False,
            blocked_reason="Canonical mission evidence is unavailable or contradictory.",
            remaining_failed_checks=(),
            next_action="Restore the canonical mission evidence before retrying runtime stabilization.",
        )

    existing = mission.get("executable_change_set")
    if isinstance(existing, dict) and existing.get("change_set_status") == "change_set_ready":
        return RuntimeStabilizationResult(
            mission_id=normalized,
            status="stable",
            change_set_status="change_set_ready",
            attempted=False,
            retryable=False,
            blocked_reason=None,
            remaining_failed_checks=(),
            next_action="Review the prepared change set through the existing founder approval gate.",
        )

    result = generate_executable_change_set(
        {
            "mission_id": normalized,
            "provider": provider,
            "model": model,
            "progress_observer": progress_observer,
        }
    )
    record_execution_mission_evidence(normalized, "executable_change_set", result)

    validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
    remaining = validation.get("remaining_failed_checks")
    remaining_checks = tuple(item for item in (remaining or []) if isinstance(item, dict))
    ready = result.get("change_set_status") == "change_set_ready"

    return RuntimeStabilizationResult(
        mission_id=normalized,
        status="stable" if ready else "blocked",
        change_set_status=str(result.get("change_set_status") or "blocked"),
        attempted=True,
        retryable=not ready,
        blocked_reason=None if ready else str(result.get("blocked_reason") or "Runtime stabilization did not produce a valid change set."),
        remaining_failed_checks=remaining_checks,
        next_action=(
            "Review the prepared change set through the existing founder approval gate."
            if ready
            else str(result.get("next_action") or "Review validation evidence and retry runtime stabilization.")
        ),
    )
