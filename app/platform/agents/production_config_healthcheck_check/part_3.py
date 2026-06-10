# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import ast
from pathlib import Path
from typing import Any, Dict, Iterable, List
from app.platform.services.production_config_service import (
    PRODUCTION_CONFIG_SAFETY_MODE,
    build_healthcheck_summary,
    build_provider_checklist,
    inspect_production_config,
)
ROOT = Path(__file__).resolve().parents[3]
ENV_EXAMPLE_PATH = ROOT / ".env.example"
MAIN_PATH = ROOT / "app" / "main.py"
PLATFORM_ROUTES_PATH = ROOT / "app" / "platform" / "api" / "routes.py"
REQUIRED_ENV_NAMES = {
    "DATABASE_URL",
    "PLATFORM_DATABASE_URL",
    "JWT_SECRET_KEY",
    "PLATFORM_INTERNAL_TOKEN",
    "OPENAI_API_KEY",
}
OPTIONAL_ENV_NAMES = {
    "OPENAI_MODEL",
    "JWT_ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "LANGCHAIN_TRACING_V2",
    "LANGCHAIN_PROJECT",
    "LANGSMITH_API_KEY",
}
FORBIDDEN_SECRET_FRAGMENTS = [
    "sk-proj-",
    "sk-",
    "xoxb-",
    "ghp_",
    "github_pat_",
    "AIza",
    "AKIA",
    "ASIA",
    "postgresql://postgres:",
    "mysql://root:",
]
EXPECTED_FALSE_SAFETY_FLAGS = {
    "deployment_performed",
    "runtime_server_started",
    "generated_code_execution_performed",
    "generated_files_written",
    "filesystem_write_performed",
    "production_file_write_performed",
    "live_module_modified",
    "install_packages_performed",
    "auto_approval_performed",
    "approval_bypass_performed",
    "repair_applied",
    "unapproved_repair_applied",
    "restore_executed",
    "module_rollout_performed",
    "rollout_execution_performed",
}

def run_check() -> Dict[str, Any]:
    failures = _failures()
    _check_service_contract(failures)
    _check_env_example(failures)
    _check_routes(failures)
    return {
        "passed": not failures,
        "milestone": "V81 — Production Config & Healthcheck",
        "safety_mode": PRODUCTION_CONFIG_SAFETY_MODE,
        "checks": {
            "service_contract": True,
            "env_example_placeholders": True,
            "route_registration_static_check": True,
            "secret_exposure_static_check": True,
            "safety_boundary_flags": True,
        },
        "failures": failures,
    }

def main() -> int:
    result = run_check()
    print(result)
    return 0 if result["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
