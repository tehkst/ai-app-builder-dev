from __future__ import annotations

import os
from typing import Any

SMTP_PROVIDERS = {
    "sendgrid": {
        "label": "SendGrid",
        "host": "smtp.sendgrid.net",
        "port": 587,
        "username_env": "SMTP_USERNAME",
        "password_env": "SMTP_PASSWORD",
        "sender_env": "EMAIL_FROM",
        "secret_name": "smtp-password",
    },
    "gmail": {
        "label": "Gmail",
        "host": "smtp.gmail.com",
        "port": 587,
        "username_env": "GMAIL_ADDRESS",
        "password_env": "GMAIL_APP_PASSWORD",
        "sender_env": "GMAIL_ADDRESS",
        "secret_name": "gmail-app-password",
    },
}


def selected_smtp_provider(value: str | None = None) -> str:
    if value:
        provider = value.strip().lower()
    else:
        from app.platform.runtime.settings_store import SMTP_PROVIDER_KEY, get_setting

        provider = (get_setting(SMTP_PROVIDER_KEY) or os.getenv("SMTP_PROVIDER") or "sendgrid").strip().lower()
    return provider if provider in SMTP_PROVIDERS else "sendgrid"


def provider_configured(provider: str) -> bool:
    config = SMTP_PROVIDERS[provider]
    return bool(os.getenv(config["username_env"]) and os.getenv(config["password_env"]))


def save_smtp_provider_selection(payload: dict[str, Any]) -> dict[str, Any]:
    from app.platform.runtime.settings_store import SMTP_PROVIDER_KEY, set_setting

    provider = str(payload.get("provider") or "").strip().lower()
    if provider not in SMTP_PROVIDERS:
        raise ValueError("The selected email provider is not supported.")
    set_setting(SMTP_PROVIDER_KEY, provider)
    return smtp_provider_status()


def smtp_provider_status(provider: str | None = None) -> dict[str, Any]:
    active = selected_smtp_provider(provider)
    providers = {
        name: {
            "configured": provider_configured(name),
            "secret_name": config["secret_name"],
            "host": config["host"],
            "label": config["label"],
        }
        for name, config in SMTP_PROVIDERS.items()
    }
    current = providers[active]
    return {
        "provider": active,
        "status": "configured" if current["configured"] else "missing-secret",
        "secret_name": current["secret_name"],
        "host": current["host"],
        "credential_visible": False,
        "available_providers": providers,
    }


def active_smtp_config() -> dict[str, Any]:
    provider = selected_smtp_provider()
    config = SMTP_PROVIDERS[provider]
    username = os.getenv(config["username_env"], "")
    return {
        "provider": provider,
        "host": config["host"],
        "port": config["port"],
        "username": username,
        "password": os.getenv(config["password_env"], ""),
        "sender": os.getenv(config["sender_env"], "") or username,
    }
