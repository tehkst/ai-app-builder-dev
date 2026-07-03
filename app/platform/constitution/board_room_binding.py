from __future__ import annotations

from typing import Any

from app.platform.constitution.runtime import build_constitution_context
from app.platform.executive_decision.service import decide_next_action
from app.platform.operating_console import service as base_console


def build_operating_console_summary() -> dict[str, Any]:
    result = base_console.build_operating_console_summary()
    result["runtime_constitution"] = build_constitution_context()
    result["status"] = "constitution-bound-board-room-ready"
    result["executive_decision_center"] = {"status": "ready", "purpose": "Choose contextual Board Room actions instead of a fixed workflow button."}
    return result


def build_dashboard_state() -> dict[str, Any]:
    return base_console.build_dashboard_state()


def chat_with_operating_console(payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)
    enriched["runtime_constitution"] = build_constitution_context()
    result = base_console.chat_with_operating_console(enriched)
    result["runtime_constitution"] = enriched["runtime_constitution"]
    result.setdefault("governance", {})["runtime_constitution_required"] = True
    decision = decide_next_action({"message": result.get("founder_message") or enriched.get("message") or enriched.get("prompt") or "", "conversation_intelligence": result.get("conversation_intelligence") or {}, "runtime_constitution": enriched["runtime_constitution"]})
    result["executive_decision"] = decision
    result["next_step"] = decision.get("reason") or result.get("next_step")
    return result


def run_console_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)
    enriched["runtime_constitution"] = build_constitution_context()
    result = base_console.run_console_workflow(enriched)
    result["runtime_constitution"] = enriched["runtime_constitution"]
    result["executive_decision"] = decide_next_action({"message": enriched.get("message") or enriched.get("request") or enriched.get("prompt") or "", "conversation_intelligence": result.get("conversation_intelligence") or {}, "runtime_constitution": enriched["runtime_constitution"]})
    return result
