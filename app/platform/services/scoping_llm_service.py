from __future__ import annotations

import json
import os
from typing import Any, Dict

from app.ai.llm import invoke_llm


def enrich_scope_with_llm(payload: Dict[str, Any]) -> Dict[str, Any]:
    if os.getenv("PLATFORM_SCOPING_LLM_ENABLED", "").lower() not in {"1", "true", "yes"}:
        return {"status": "disabled", "notes": {"reason": "PLATFORM_SCOPING_LLM_ENABLED is not enabled"}}

    prompt = _prompt(payload)
    try:
        response = invoke_llm(prompt, node_name="platform_scoping_gateway", metadata={"safe_mode": True})
        raw = getattr(response, "content", str(response))
        return {"status": "completed", "notes": _parse_json(raw), "raw": raw[:4000]}
    except Exception as error:  # pragma: no cover - network/provider dependent
        return {"status": "failed", "notes": {"error": str(error)}}


def _prompt(payload: Dict[str, Any]) -> str:
    return (
        "You are a production scoping agent for an AI Software Factory. "
        "Return strict JSON with optional keys: clarification_questions, "
        "scope_risks, milestone_suggestions. Do not propose writing files, "
        "executing code, or deploying without explicit approval. Request:\n"
        f"{json.dumps(payload, indent=2, sort_keys=True)}"
    )


def _parse_json(raw: str) -> Dict[str, Any]:
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {"llm_value": data}
    except json.JSONDecodeError:
        return {"summary": raw[:1000]}
