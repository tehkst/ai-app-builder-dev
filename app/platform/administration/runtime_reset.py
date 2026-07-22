from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

CONFIRMATION_PHRASE = "RESET JARVIS TEST RUNTIME"


@dataclass(frozen=True)
class ResetScope:
    key: str
    description: str
    preserved: bool = False


RESET_SCOPES: tuple[ResetScope, ...] = (
    ResetScope("missions", "Execution missions and canonical mission evidence"),
    ResetScope("planning", "Planning, architecture review, engineering breakdowns, and change sets"),
    ResetScope("executive_inbox", "Executive Inbox operational items"),
    ResetScope("board_room", "Board Room sessions and decisions"),
    ResetScope("jarvis_conversations", "Jarvis acceptance-test conversation history"),
    ResetScope("workflow_runtime", "Durable workflow runs and runtime execution state"),
    ResetScope("github_cache", "Cached GitHub, pull-request, and CI observations"),
    ResetScope("deployment_evidence", "Cached deployment and production-verification evidence"),
    ResetScope("agent_sessions", "Agent session state"),
    ResetScope("mission_memory", "Mission-associated memory where the canonical memory service supports deletion"),
)

PRESERVED_SCOPES: tuple[ResetScope, ...] = (
    ResetScope("users_auth_roles", "Users, authentication, roles, and permissions", True),
    ResetScope("platform_configuration", "Platform settings, Runtime Constitution, model configuration, and installed capabilities", True),
    ResetScope("source_and_git", "Source code, Git history, branches, pull requests, and external GitHub history", True),
    ResetScope("deployment_infrastructure", "Live deployment infrastructure, traffic, secrets, and deployment configuration", True),
)

ResetPreview = Callable[[], dict[str, Any]]
ResetExecute = Callable[[], dict[str, Any]]
ResetVerify = Callable[[], dict[str, Any]]


class RuntimeResetRegistry:
    """Thin administration registry for canonical reset handlers.

    Domain owners register their own preview, execute, and verify functions. This
    class deliberately does not know database tables and never performs broad SQL
    deletion.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, tuple[ResetPreview, ResetExecute, ResetVerify]] = {}

    def register(self, scope: str, *, preview: ResetPreview, execute: ResetExecute, verify: ResetVerify) -> None:
        if scope not in {item.key for item in RESET_SCOPES}:
            raise ValueError(f"Unsupported reset scope: {scope}")
        if scope in self._handlers:
            raise ValueError(f"Reset scope already registered: {scope}")
        self._handlers[scope] = (preview, execute, verify)

    def preview(self) -> dict[str, Any]:
        return {
            "status": "preview-ready",
            "confirmation_required": True,
            "confirmation_phrase": CONFIRMATION_PHRASE,
            "clear": [self._preview_scope(item) for item in RESET_SCOPES],
            "preserve": [item.__dict__ for item in PRESERVED_SCOPES],
            "external_systems_touched": False,
        }

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        if str(payload.get("authorization_status") or "").lower() != "approved":
            return self._blocked("Administrative authorization is required.")
        if str(payload.get("confirmation") or "") != CONFIRMATION_PHRASE:
            return self._blocked("Exact reset confirmation phrase is required.")
        if payload.get("preview_acknowledged") is not True:
            return self._blocked("Reset preview must be acknowledged before execution.")

        results: list[dict[str, Any]] = []
        failed = False
        for item in RESET_SCOPES:
            handler = self._handlers.get(item.key)
            if handler is None:
                failed = True
                results.append({
                    "scope": item.key,
                    "status": "unsupported",
                    "cleared": 0,
                    "message": "Canonical reset handler is not registered.",
                })
                continue
            try:
                outcome = dict(handler[1]() or {})
                outcome.setdefault("scope", item.key)
                outcome.setdefault("status", "cleared")
                outcome.setdefault("cleared", 0)
                results.append(outcome)
                failed = failed or outcome.get("status") not in {"cleared", "already-clean"}
            except Exception as exc:  # surfaced as evidence; registry must continue
                failed = True
                results.append({
                    "scope": item.key,
                    "status": "failed",
                    "cleared": 0,
                    "message": f"{type(exc).__name__}: {exc}",
                })

        verification = self.verify()
        stale_mission_present = any(
            "MISSION-44BE9D1DAF0E" in str(item)
            for item in verification.get("details", [])
        )
        return {
            "status": "partial-failure" if failed or not verification.get("clean") else "reset-complete",
            "results": results,
            "verification": verification,
            "stale_mission_present": stale_mission_present,
            "preserved": [item.__dict__ for item in PRESERVED_SCOPES],
            "external_systems_touched": False,
        }

    def verify(self) -> dict[str, Any]:
        details: list[dict[str, Any]] = []
        clean = True
        for item in RESET_SCOPES:
            handler = self._handlers.get(item.key)
            if handler is None:
                clean = False
                details.append({"scope": item.key, "status": "unsupported", "remaining": None})
                continue
            try:
                outcome = dict(handler[2]() or {})
                outcome.setdefault("scope", item.key)
                outcome.setdefault("remaining", 0)
                details.append(outcome)
                clean = clean and int(outcome.get("remaining") or 0) == 0
            except Exception as exc:
                clean = False
                details.append({
                    "scope": item.key,
                    "status": "verification-failed",
                    "remaining": None,
                    "message": f"{type(exc).__name__}: {exc}",
                })
        return {"status": "clean" if clean else "not-clean", "clean": clean, "details": details}

    def _preview_scope(self, item: ResetScope) -> dict[str, Any]:
        handler = self._handlers.get(item.key)
        if handler is None:
            return {**item.__dict__, "status": "unsupported", "records": None}
        try:
            outcome = dict(handler[0]() or {})
            outcome.setdefault("records", 0)
            return {**item.__dict__, "status": "ready", **outcome}
        except Exception as exc:
            return {
                **item.__dict__,
                "status": "preview-failed",
                "records": None,
                "message": f"{type(exc).__name__}: {exc}",
            }

    @staticmethod
    def _blocked(reason: str) -> dict[str, Any]:
        return {
            "status": "blocked",
            "blocked_reason": reason,
            "confirmation_phrase": CONFIRMATION_PHRASE,
            "external_systems_touched": False,
        }


runtime_reset_registry = RuntimeResetRegistry()


def preview_runtime_reset() -> dict[str, Any]:
    return runtime_reset_registry.preview()


def execute_runtime_reset(payload: dict[str, Any]) -> dict[str, Any]:
    return runtime_reset_registry.execute(payload)


def verify_runtime_reset() -> dict[str, Any]:
    return runtime_reset_registry.verify()
