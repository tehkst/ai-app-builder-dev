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

class EnvCheck:
    name: str
    configured: bool
    required_for: str
    secret: bool
    purpose: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "configured": self.configured,
            "required_for": self.required_for,
            "secret": self.secret,
            "purpose": self.purpose,
        }

def _safe_flags() -> Dict[str, bool]:
    return {
        "production_config_checked": True,
        "readiness_only": True,
        "deployment_performed": False,
        "runtime_server_started": False,
        "generated_code_execution_performed": False,
        "generated_files_written": False,
        "filesystem_write_performed": False,
        "production_file_write_performed": False,
        "live_module_modified": False,
        "install_packages_performed": False,
        "auto_approval_performed": False,
        "approval_bypass_performed": False,
        "repair_applied": False,
        "unapproved_repair_applied": False,
        "restore_executed": False,
        "module_rollout_performed": False,
        "rollout_execution_performed": False,
    }

def _configured(name: str) -> bool:
    value = os.getenv(name)
    return value is not None and value.strip() != ""

def get_required_env_checks() -> List[Dict[str, Any]]:
    checks = []
    for item in _REQUIRED_ENV:
        checks.append(
            EnvCheck(
                name=item["name"],
                configured=_configured(item["name"]),
                required_for=item["required_for"],
                secret=bool(item["secret"]),
                purpose=item["purpose"],
            ).to_dict()
        )
    return checks
