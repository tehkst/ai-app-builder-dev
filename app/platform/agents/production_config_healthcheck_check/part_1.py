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

def _failures() -> List[str]:
    return []

def _assert(condition: bool, message: str, failures: List[str]) -> None:
    if not condition:
        failures.append(message)

def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def _extract_route_paths(path: Path) -> List[str]:
    tree = ast.parse(_read_text(path))
    routes: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in {"get", "post", "put", "patch", "delete"}:
                continue
            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                if isinstance(decorator.args[0].value, str):
                    routes.append(decorator.args[0].value)
    return routes

def _flatten_values(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _flatten_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _flatten_values(item)
    else:
        yield str(value)

def _assert_no_secret_values(payload: Dict[str, Any], failures: List[str]) -> None:
    flattened = "\n".join(_flatten_values(payload))
    for fragment in FORBIDDEN_SECRET_FRAGMENTS:
        _assert(fragment not in flattened, f"secret-looking fragment exposed in payload: {fragment}", failures)
