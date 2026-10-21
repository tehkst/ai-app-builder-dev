"""Token usage as the AI providers report it, in one shape (priced in app/platform/ai_costs)."""
from __future__ import annotations

from typing import Any, Dict


def normalize(usage: Dict[str, Any]) -> Dict[str, int]:
    """One shape for every provider: {"input", "cached", "output"} tokens. `input` includes cached.
    OpenAI Responses: input_tokens / output_tokens / input_tokens_details.cached_tokens.
    DeepSeek (chat completions): prompt_tokens / completion_tokens / prompt_cache_hit_tokens."""
    usage = usage or {}

    def number(*keys: str) -> int:
        for key in keys:
            value = usage.get(key)
            if isinstance(value, (int, float)):
                return int(value)
        return 0

    details = usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {}
    cached = number("prompt_cache_hit_tokens") or int((details or {}).get("cached_tokens") or 0)
    return {"input": number("input_tokens", "prompt_tokens"), "cached": cached,
            "output": number("output_tokens", "completion_tokens")}


def add_usage(total: Dict[str, Any], provider: str, model: str, usage: Dict[str, Any]) -> None:
    """Add one model reply to a running total (one total per provider+model)."""
    tokens = normalize(usage)
    total["provider"], total["model"] = total.get("provider") or provider, total.get("model") or model
    total["calls"] = total.get("calls", 0) + 1
    for key, value in tokens.items():
        total[key] = total.get(key, 0) + value
