from __future__ import annotations

from typing import Any

from app.platform.constitution.runtime import build_constitution_context
from app.platform.operating_console import service as base_console


def build_operating_console_summary() -> dict[str, Any]:
    result = base_console.build_operating_console_summary()
    result["runtime_constitution"] = build_constitution_context()
    result["status"] = "constitution-bound-board-room-ready"
    return result


def build_dashboard_state() -> dict[str, Any]:
    return base_console.build_dashboard_state()


def chat_with_operating_console(payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)
    enriched["runtime_constitution"] = build_constitution_context()
    result = base_console.chat_with_operating_console(enriched)
    result["runtime_constitution"] = enriched["runtime_constitution"]
    result.setdefault("governance", {})["runtime_constitution_required"] = True
    return result


def run_console_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)
    enriched["runtime_constitution"] = build_constitution_context()
    result = base_console.run_console_workflow(enriched)
    result["runtime_constitution"] = enriched["runtime_constitution"]
    return result
