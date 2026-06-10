# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any, Dict, List
PRODUCTION_CONFIG_SAFETY_MODE = "production_config_v81_readiness_only"
_REQUIRED_ENV = [
    {
        "name": "DATABASE_URL",
        "purpose": "Primary application database URL.",
        "required_for": "hosted_mvp",
        "secret": True,
    },
    {
        "name": "PLATFORM_DATABASE_URL",
        "purpose": "Platform persistence database URL. May match DATABASE_URL for private MVP.",
        "required_for": "hosted_mvp",
        "secret": True,
    },
    {
        "name": "JWT_SECRET_KEY",
        "purpose": "JWT signing secret for API authentication.",
        "required_for": "hosted_mvp",
        "secret": True,
    },
    {
        "name": "PLATFORM_INTERNAL_TOKEN",
        "purpose": "Internal/admin API gate token for platform routes.",
        "required_for": "hosted_mvp",
        "secret": True,
    },
    {
        "name": "OPENAI_API_KEY",
        "purpose": "OpenAI API key for generation and analysis calls.",
        "required_for": "ai_generation",
        "secret": True,
    },
]
_OPTIONAL_ENV = [
    {
        "name": "OPENAI_MODEL",
        "purpose": "OpenAI model override.",
        "default": "gpt-4o-mini",
        "secret": False,
    },
    {
        "name": "JWT_ALGORITHM",
        "purpose": "JWT signing algorithm.",
        "default": "HS256",
        "secret": False,
    },
    {
        "name": "ACCESS_TOKEN_EXPIRE_MINUTES",
        "purpose": "Access-token expiry in minutes.",
        "default": "60",
        "secret": False,
    },
    {
        "name": "LANGCHAIN_TRACING_V2",
        "purpose": "LangSmith tracing toggle.",
        "default": "false",
        "secret": False,
    },
    {
        "name": "LANGCHAIN_PROJECT",
        "purpose": "LangSmith project name.",
        "default": "AI-Software-Factory",
        "secret": False,
    },
    {
        "name": "LANGSMITH_API_KEY",
        "purpose": "LangSmith API key when tracing is enabled.",
        "default": "",
        "secret": True,
    },
]

def build_healthcheck_summary() -> Dict[str, Any]:
    config = inspect_production_config()
    return {
        "ok": True,
        "service": "ai-software-factory",
        "safety_mode": PRODUCTION_CONFIG_SAFETY_MODE,
        "readiness": config["status"],
        "hosted_mvp_ready": config["hosted_mvp_ready"],
        "missing_required_env": config["missing_required_env"],
        "safety_flags": _safe_flags(),
    }
