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

def run_auth_admin_access_gate_check() -> Dict[str, Any]:
    _configure_test_auth()
    checks: Dict[str, bool] = {}

    missing_status = _capture_http_status(lambda: _call_guard())
    wrong_internal_status = _capture_http_status(lambda: _call_guard(internal_token="wrong-token"))
    internal_result: Dict[str, Any] = {}
    internal_status = _capture_http_status(
        lambda: internal_result.update(_call_guard(internal_token=_TEST_INTERNAL_TOKEN))
    )
    invalid_login_status = _capture_http_status(
        lambda: platform_security.platform_admin_login(
            username=_TEST_ADMIN_USERNAME,
            password="wrong-password",
        )
    )
    login_result: Dict[str, Any] = {}
    login_status = _capture_http_status(
        lambda: login_result.update(
            platform_security.platform_admin_login(
                username=_TEST_ADMIN_USERNAME,
                password=_TEST_ADMIN_PASSWORD,
            )
        )
    )
    access_token = login_result.get("access_token", "")
    jwt_result: Dict[str, Any] = {}
    jwt_status = _capture_http_status(
        lambda: jwt_result.update(_call_guard(authorization=f"Bearer {access_token}"))
    )
    invalid_jwt_status = _capture_http_status(
        lambda: _call_guard(authorization="Bearer invalid.jwt.token")
    )
    production_internal_status = _production_internal_token_status()

    checks["missing_auth_rejected"] = missing_status == 401
    checks["wrong_internal_token_rejected"] = wrong_internal_status == 403
    checks["internal_token_still_works"] = (
        internal_status == 200 and internal_result.get("auth_mode") == "internal_token"
    )
    checks["invalid_login_rejected"] = invalid_login_status == 401
    checks["admin_login_returns_jwt"] = login_status == 200 and bool(access_token)
    checks["jwt_bearer_token_works"] = (
        jwt_status == 200 and jwt_result.get("auth_mode") == "jwt_bearer"
    )
    checks["invalid_jwt_rejected"] = invalid_jwt_status == 403
    checks["production_internal_token_fallback_blocked"] = production_internal_status == 401

    audit_events = _latest_auth_events()
    event_types = {event["event_type"] for event in audit_events}
    checks["audit_events_recorded"] = {
        "platform_api_auth_missing",
        "platform_api_auth_invalid",
        "platform_api_auth_success",
        "platform_admin_login_invalid",
        "platform_admin_login_success",
        "platform_api_jwt_success",
        "platform_api_jwt_invalid",
        "platform_api_internal_token_disabled",
    }.issubset(event_types)

    safety_flags = _safe_flags()
    checks["safety_flags_preserved"] = _safe_flags_preserved(safety_flags)

    samples = {
        "status_codes": {
            "missing": missing_status,
            "wrong_internal": wrong_internal_status,
            "internal_ok": internal_status,
            "invalid_login": invalid_login_status,
            "login": login_status,
            "jwt_ok": jwt_status,
            "invalid_jwt": invalid_jwt_status,
            "production_internal_blocked": production_internal_status,
        },
        "auth_modes": {
            "internal": internal_result.get("auth_mode"),
            "jwt": jwt_result.get("auth_mode"),
            "login": login_result.get("auth_mode"),
        },
        "audit_event_types": sorted(event_types),
        "safety_flags": safety_flags,
    }

    passed = all(checks.values())
    return {
        "check": "auth_admin_access_gate_check",
        "milestone": "V83 — Auth & Admin Access Gate",
        "passed": passed,
        "safety_mode": V83_AUTH_ADMIN_ACCESS_GATE_SAFETY_MODE,
        "checks": checks,
        "samples": samples,
    }

def _production_internal_token_status() -> int:
    os.environ["PLATFORM_ALLOW_INTERNAL_TOKEN_FALLBACK"] = "false"
    os.environ["RAILWAY_ENVIRONMENT_NAME"] = "production"
    importlib.reload(platform_security)
    status = _capture_http_status(lambda: _call_guard(internal_token=_TEST_INTERNAL_TOKEN))
    _configure_test_auth()
    return status

def main() -> int:
    result = run_auth_admin_access_gate_check()
    print(result)
    return 0 if result["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
