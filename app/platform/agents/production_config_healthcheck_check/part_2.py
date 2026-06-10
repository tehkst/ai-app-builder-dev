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

def _check_service_contract(failures: List[str]) -> None:
    config = inspect_production_config()
    health = build_healthcheck_summary()
    checklist = build_provider_checklist()

    _assert(config.get("success") is True, "config inspection should succeed", failures)
    _assert(
        config.get("safety_mode") == PRODUCTION_CONFIG_SAFETY_MODE,
        "config safety mode should match V81 readiness-only mode",
        failures,
    )
    _assert(
        PRODUCTION_CONFIG_SAFETY_MODE == "production_config_v81_readiness_only",
        "unexpected production config safety mode",
        failures,
    )

    required_names = {item.get("name") for item in config.get("required_env", [])}
    optional_names = {item.get("name") for item in config.get("optional_env", [])}
    _assert(REQUIRED_ENV_NAMES.issubset(required_names), "required env checklist is incomplete", failures)
    _assert(OPTIONAL_ENV_NAMES.issubset(optional_names), "optional env checklist is incomplete", failures)

    for item in config.get("required_env", []) + config.get("optional_env", []):
        _assert("configured" in item, f"missing configured flag for {item.get('name')}", failures)
        _assert("value" not in item, f"secret/config value leaked for {item.get('name')}", failures)

    safety_flags = config.get("safety_flags", {})
    _assert(safety_flags.get("readiness_only") is True, "readiness_only flag must be true", failures)
    _assert(safety_flags.get("production_config_checked") is True, "production_config_checked flag must be true", failures)
    for flag in EXPECTED_FALSE_SAFETY_FLAGS:
        _assert(safety_flags.get(flag) is False, f"safety flag should remain false: {flag}", failures)

    _assert(health.get("ok") is True, "health summary should remain ok", failures)
    _assert("missing_required_env" in health, "health summary should include missing env names", failures)
    _assert("safety_flags" in health, "health summary should include safety flags", failures)

    _assert(checklist.get("recommended_first_provider") == "Railway", "Railway should remain first provider", failures)
    _assert("railway" in checklist, "Railway checklist missing", failures)
    _assert("gcore" in checklist, "Gcore checklist missing", failures)

    _assert_no_secret_values(config, failures)
    _assert_no_secret_values(health, failures)
    _assert_no_secret_values(checklist, failures)

def _check_env_example(failures: List[str]) -> None:
    text = _read_text(ENV_EXAMPLE_PATH)
    for name in REQUIRED_ENV_NAMES | OPTIONAL_ENV_NAMES:
        _assert(f"{name}=" in text, f".env.example missing placeholder for {name}", failures)

    for fragment in FORBIDDEN_SECRET_FRAGMENTS:
        _assert(fragment not in text, f".env.example contains secret-looking fragment: {fragment}", failures)

    placeholder_markers = [
        "username:password@host",
        "replace_with_secure_secret",
        "replace_with_internal_admin_token",
        "replace_with_openai_api_key",
    ]
    for marker in placeholder_markers:
        _assert(marker in text, f".env.example missing placeholder marker: {marker}", failures)

def _check_routes(failures: List[str]) -> None:
    main_routes = set(_extract_route_paths(MAIN_PATH))
    platform_routes = set(_extract_route_paths(PLATFORM_ROUTES_PATH))

    _assert("/health" in main_routes, "/health route missing", failures)
    _assert("/health/readiness" in main_routes, "/health/readiness route missing", failures)
    _assert("/config/readiness" in platform_routes, "/platform/config/readiness route missing", failures)
    _assert("/config/checklist" in platform_routes, "/platform/config/checklist route missing", failures)

    main_text = _read_text(MAIN_PATH)
    platform_routes_text = _read_text(PLATFORM_ROUTES_PATH)
    _assert("build_healthcheck_summary" in main_text, "main healthcheck should use V81 health summary", failures)
    _assert("inspect_production_config" in platform_routes_text, "platform readiness should use config service", failures)
    _assert("build_provider_checklist" in platform_routes_text, "platform checklist should use provider checklist", failures)
    _assert("require_platform_admin" in platform_routes_text, "platform config routes should remain admin-gated", failures)
