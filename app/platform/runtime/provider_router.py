from __future__ import annotations

import os
from typing import Any

from app.platform.runtime.ai_provider import AIProviderError, AIProviderResult, invoke_openai, provider_configured
from app.platform.runtime.deepseek_provider import deepseek_configured, invoke_deepseek

SUPPORTED_MODELS = {
    "openai": ("gpt-5.5", "gpt-5.5-mini", "gpt-5.5-thinking"),
    "deepseek": ("deepseek-v4-pro", "deepseek-v4-flash"),
}


def selected_provider(value: str | None = None) -> str:
    if value:
        provider = value.strip().lower()
    else:
        from app.platform.runtime.settings_store import AI_PROVIDER_KEY, get_setting

        provider = (get_setting(AI_PROVIDER_KEY) or os.getenv("AI_PROVIDER") or "openai").strip().lower()
    return provider if provider in {"openai", "deepseek"} else "openai"


def default_model(provider: str | None = None) -> str:
    from app.platform.runtime.settings_store import AI_MODEL_KEY, get_setting

    resolved = selected_provider(provider)
    persisted_model = get_setting(AI_MODEL_KEY)
    if persisted_model and persisted_model in SUPPORTED_MODELS[resolved]:
        return persisted_model
    if resolved == "deepseek":
        return os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    return os.getenv("OPENAI_MODEL", "gpt-5.5")


def save_ai_provider_selection(payload: dict[str, Any]) -> dict[str, Any]:
    from app.platform.runtime.settings_store import AI_MODEL_KEY, AI_PROVIDER_KEY, set_setting

    provider = str(payload.get("provider") or "").strip().lower()
    if provider not in SUPPORTED_MODELS:
        raise ValueError("The selected AI provider is not supported.")
    model = str(payload.get("model") or "").strip() or default_model(provider)
    if model not in SUPPORTED_MODELS[provider]:
        raise ValueError("The selected model is not supported by the chosen AI provider.")
    set_setting(AI_PROVIDER_KEY, provider)
    set_setting(AI_MODEL_KEY, model)
    return provider_status()


def provider_status(provider: str | None = None) -> dict[str, Any]:
    active = selected_provider(provider)
    providers = {
        "openai": {
            "configured": provider_configured(),
            "secret_name": "OPENAI_API_KEY",
            "model": default_model("openai"),
        },
        "deepseek": {
            "configured": deepseek_configured(),
            "secret_name": "DEEPSEEK_API_KEY",
            "model": default_model("deepseek"),
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
    explicit_provider = str(provider or "").strip().lower()
    if explicit_provider and explicit_provider not in SUPPORTED_MODELS:
        raise AIProviderError("The selected AI provider is not supported.")
    active = selected_provider(provider)
    selected_model = model or default_model(active)
    if selected_model not in SUPPORTED_MODELS[active]:
        raise AIProviderError(
            "The selected model is not supported by the configured AI provider."
        )
    if active == "deepseek":
        return invoke_deepseek(prompt=prompt, system=system, model=selected_model)
    return invoke_openai(prompt=prompt, system=system, model=selected_model)
