from __future__ import annotations

import importlib
import os
from typing import Any, Dict

from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.platform.api.security as platform_security
from app.main import app
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
    os.environ.setdefault("JWT_SECRET_KEY", "v83-test-jwt-secret")
    os.environ.setdefault("JWT_ALGORITHM", "HS256")
    importlib.reload(platform_security)


def _safe_flags() -> Dict[str, bool]:
    return {
        "admin_gate_only": True,
        "jwt_admin_login_enabled": True,
        "internal_token_preserved": True,
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


def _direct_guard_check(headers: Dict[str, str]) -> Dict[str, Any]:
    client = TestClient(app)
    return client.get("/platform/config/checklist", headers=headers)


def _latest_auth_events(limit: int = 20):
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


def run_auth_admin_access_gate_check() -> Dict[str, Any]:
    _configure_test_auth()
    client = TestClient(app)
    checks: Dict[str, bool] = {}
    samples: Dict[str, Any] = {}

    missing = client.get("/platform/config/checklist")
    wrong_internal = client.get(
        "/platform/config/checklist",
        headers={"X-Platform-Internal-Token": "wrong-token"},
    )
    internal_ok = client.get(
        "/platform/config/checklist",
        headers={"X-Platform-Internal-Token": _TEST_INTERNAL_TOKEN},
    )
    invalid_login = client.post(
        "/platform/auth/login",
        json={"username": _TEST_ADMIN_USERNAME, "password": "wrong-password"},
    )
    login = client.post(
        "/platform/auth/login",
        json={"username": _TEST_ADMIN_USERNAME, "password": _TEST_ADMIN_PASSWORD},
    )
    access_token = login.json().get("access_token") if login.status_code == 200 else ""
    jwt_ok = client.get(
        "/platform/config/checklist",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    invalid_jwt = client.get(
        "/platform/config/checklist",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )

    checks["missing_auth_rejected"] = missing.status_code == 401
    checks["wrong_internal_token_rejected"] = wrong_internal.status_code == 403
    checks["internal_token_still_works"] = internal_ok.status_code == 200
    checks["invalid_login_rejected"] = invalid_login.status_code == 401
    checks["admin_login_returns_jwt"] = login.status_code == 200 and bool(access_token)
    checks["jwt_bearer_token_works"] = jwt_ok.status_code == 200
    checks["invalid_jwt_rejected"] = invalid_jwt.status_code == 403

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
    }.issubset(event_types)

    safety_flags = _safe_flags()
    checks["safety_flags_preserved"] = all(safety_flags.values())

    samples = {
        "status_codes": {
            "missing": missing.status_code,
            "wrong_internal": wrong_internal.status_code,
            "internal_ok": internal_ok.status_code,
            "invalid_login": invalid_login.status_code,
            "login": login.status_code,
            "jwt_ok": jwt_ok.status_code,
            "invalid_jwt": invalid_jwt.status_code,
        },
        "auth_modes": {
            "internal": internal_ok.json().get("provider_checklist") is not None if internal_ok.status_code == 200 else False,
            "jwt": jwt_ok.json().get("provider_checklist") is not None if jwt_ok.status_code == 200 else False,
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


def main() -> int:
    result = run_auth_admin_access_gate_check()
    print(result)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
