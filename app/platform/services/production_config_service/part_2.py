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

def get_optional_env_checks() -> List[Dict[str, Any]]:
    checks = []
    for item in _OPTIONAL_ENV:
        checks.append(
            {
                "name": item["name"],
                "configured": _configured(item["name"]),
                "default": item.get("default", ""),
                "secret": bool(item["secret"]),
                "purpose": item["purpose"],
            }
        )
    return checks

def build_provider_checklist() -> Dict[str, Any]:
    return {
        "recommended_first_provider": "gcp_cloud_run",
        "gcp_cloud_run": {
            "required_steps": [
                "Merge to main and dispatch .github/workflows/platform-deploy.yml for the target environment.",
                "The workflow's validate job runs app.platform.gcp.check/readiness/deploy_check/"
                "environment_topology_check and infra/scripts/gate.sh before anything is built.",
                "The deploy job runs `gcloud run deploy`, wiring secrets from GCP Secret Manager via "
                "--set-secrets and non-secret config via --set-env-vars (see the deploy job in "
                "platform-deploy.yml for the exact current list).",
                "Run production config healthcheck after deploy.",
            ],
            "notes": "GCP Cloud Run is this platform's actual, already-live production target, deployed via the "
            "platform-deploy.yml GitHub Actions workflow - not a manual per-provider setup.",
        },
    }

def inspect_production_config() -> Dict[str, Any]:
    required = get_required_env_checks()
    optional = get_optional_env_checks()
    missing_required = [item["name"] for item in required if not item["configured"]]
    hosted_ready = len(missing_required) == 0
    return {
        "success": True,
        "safety_mode": PRODUCTION_CONFIG_SAFETY_MODE,
        "status": "ready" if hosted_ready else "missing_required_env",
        "hosted_mvp_ready": hosted_ready,
        "missing_required_env": missing_required,
        "required_env": required,
        "optional_env": optional,
        "provider_checklist": build_provider_checklist(),
        "safety_flags": _safe_flags(),
    }
