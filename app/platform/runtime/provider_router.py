from __future__ import annotations

import os
from typing import Any

from app.platform.runtime.ai_provider import AIProviderResult, invoke_openai, provider_configured
from app.platform.runtime.deepseek_provider import deepseek_configured, invoke_deepseek


def selected_provider(value: str | None = None) -> str:
    provider = (value or os.getenv("AI_PROVIDER") or "openai").strip().lower()
    return provider if provider in {"openai", "deepseek"} else "openai"


def default_model(provider: str) -> str:
    if selected_provider(provider) == "deepseek":
        return os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    return os.getenv("OPENAI_MODEL", "gpt-5.5")


def provider_status(provider: str | None = None) -> dict[str, Any]:
    active = selected_provider(provider)
    providers = {
        "openai": {
            "configured": provider_configured(),
            "secret_name": "OPENAI_API_KEY",
            "model": os.getenv("OPENAI_MODEL", "gpt-5.5"),
        },
        "deepseek": {
            "configured": deepseek_configured(),
            "secret_name": "DEEPSEEK_API_KEY",
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
        },
    }
    current = providers[active]
    return {
        "provider": active,
        "status": "configured" if current["configured"] else "missing-secret",
        "model": current["model"],
        "secret_name": current["secret_name"],
        "api_key_present": current["configured"],
        "api_key_visible": False,
        "routing_mode": "selectable-provider-runtime",
        "available_providers": providers,
        "capabilities": ["text-generation", "planning", "mission-worker-preview"],
    }


def invoke_provider(*, provider: str | None, prompt: str, system: str | None, model: str | None) -> AIProviderResult:
    active = selected_provider(provider)
    selected_model = model or default_model(active)
    if active == "deepseek":
        return invoke_deepseek(prompt=prompt, system=system, model=selected_model)
    return invoke_openai(prompt=prompt, system=system, model=selected_model)
