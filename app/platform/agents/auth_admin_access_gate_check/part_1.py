# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import importlib
import os
from typing import Any, Dict
from fastapi import HTTPException, Request
from starlette.datastructures import Headers
import app.platform.api.security as platform_security
from app.platform.persistence.audit import list_audit_events
from app.platform.persistence.database import PlatformSessionLocal
V83_AUTH_ADMIN_ACCESS_GATE_SAFETY_MODE = "auth_admin_access_gate_v83_private_mvp_gate_only"
_TEST_INTERNAL_TOKEN = "v83-internal-token"
_TEST_ADMIN_USERNAME = "v83-admin"
_TEST_ADMIN_PASSWORD = "v83-password"

def _configure_test_auth() -> None:
    os.environ["PLATFORM_INTERNAL_TOKEN"] = _TEST_INTERNAL_TOKEN
    os.environ["PLATFORM_ADMIN_USERNAME"] = _TEST_ADMIN_USERNAME
    os.environ["PLATFORM_ADMIN_PASSWORD"] = _TEST_ADMIN_PASSWORD
    os.environ["PLATFORM_ALLOW_INTERNAL_TOKEN_FALLBACK"] = "true"
    os.environ.pop("RAILWAY_ENVIRONMENT_NAME", None)
    os.environ.pop("PLATFORM_ENV", None)
    os.environ.pop("ENVIRONMENT", None)
    os.environ.setdefault("JWT_SECRET_KEY", "v83-test-jwt-secret")
    os.environ.setdefault("JWT_ALGORITHM", "HS256")
    importlib.reload(platform_security)

def _fake_request(path: str = "/platform/config/checklist") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": Headers({}).raw,
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 123),
        }
    )

def _safe_flags() -> Dict[str, bool]:
    return {
        "admin_gate_only": True,
        "jwt_admin_login_enabled": True,
        "internal_token_preserved": True,
        "production_internal_token_fallback_blocked": True,
        "approval_gates_preserved": True,
        "auto_approval_performed": False,
        "approval_bypass_performed": False,
        "generated_files_written": False,
        "generated_code_execution_performed": False,
        "runtime_server_started": False,
        "repair_execution_performed": False,
        "rollout_execution_performed": False,
        "deployment_performed": False,
    }

def _safe_flags_preserved(flags: Dict[str, bool]) -> bool:
    return (
        flags.get("admin_gate_only") is True
        and flags.get("jwt_admin_login_enabled") is True
        and flags.get("internal_token_preserved") is True
        and flags.get("production_internal_token_fallback_blocked") is True
        and flags.get("approval_gates_preserved") is True
        and flags.get("auto_approval_performed") is False
        and flags.get("approval_bypass_performed") is False
        and flags.get("generated_files_written") is False
        and flags.get("generated_code_execution_performed") is False
        and flags.get("runtime_server_started") is False
        and flags.get("repair_execution_performed") is False
        and flags.get("rollout_execution_performed") is False
        and flags.get("deployment_performed") is False
    )

def _call_guard(*, internal_token: str = "", authorization: str = "") -> Dict[str, Any]:
    return platform_security.require_platform_admin(
        request=_fake_request(),
        x_platform_internal_token=internal_token,
        authorization=authorization,
    )

def _capture_http_status(callable_check) -> int:
    try:
        callable_check()
    except HTTPException as error:
        return error.status_code
    return 200

def _latest_auth_events(limit: int = 30):
    db = PlatformSessionLocal()
    try:
        return [
            {
                "event_type": event.event_type,
                "status": event.status,
                "auth_mode": event.auth_mode,
                "route": event.route,
            }
            for event in list_audit_events(db, limit=limit)
            if event.event_type.startswith("platform_api_")
            or event.event_type.startswith("platform_admin_login_")
        ]
    finally:
        db.close()
