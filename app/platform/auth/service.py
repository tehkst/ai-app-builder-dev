from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

FOUNDER_EMAIL_ENV = "FOUNDER_EMAIL"
FOUNDER_PASSWORD_ENV = "FOUNDER_PASSWORD"
SESSION_SECRET_ENV = "MISSION_CONTROL_SESSION_SECRET"
DEFAULT_FOUNDER_EMAIL = "founder@ai-software-factory.local"


def build_auth_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Founder Authentication",
        "milestone": "GCP-P1",
        "status": "auth-ready" if _password_configured() else "auth-awaiting-founder-password",
        "mode": "founder-session-token",
        "roles": ["founder", "operator", "viewer"],
        "required_secrets": [FOUNDER_PASSWORD_ENV, SESSION_SECRET_ENV],
        "configured": {
            "founder_email": _founder_email(),
            "founder_password_present": _password_configured(),
            "session_secret_present": bool(os.getenv(SESSION_SECRET_ENV)),
            "secrets_visible": False,
        },
        "endpoints": {
            "summary": "GET /mission-control/auth",
            "login": "POST /mission-control/auth/login",
            "session": "POST /mission-control/auth/session",
            "logout": "POST /mission-control/auth/logout",
        },
        "next_step": "Mount FOUNDER_PASSWORD and MISSION_CONTROL_SESSION_SECRET in Cloud Run Secret Manager for real founder login.",
    }


def login_founder(payload: dict[str, Any]) -> dict[str, Any]:
    email = str(payload.get("email") or "").strip().lower()
    password = str(payload.get("password") or "")
    expected_email = _founder_email().lower()
    expected_password = os.getenv(FOUNDER_PASSWORD_ENV)

    if not expected_password:
        return {
            "status": "blocked-missing-founder-password",
            "authenticated": False,
            "secret_name": FOUNDER_PASSWORD_ENV,
            "next_step": "Create FOUNDER_PASSWORD in Secret Manager and mount it into Cloud Run.",
        }

    if email != expected_email or not hmac.compare_digest(password, expected_password):
        return {
            "status": "invalid-credentials",
            "authenticated": False,
        }

    issued_at = _now()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
    claims = {
        "sub": email,
        "role": "founder",
        "iat": issued_at,
        "exp": expires_at.replace(microsecond=0).isoformat(),
    }
    token = _sign_claims(claims)
    return {
        "status": "authenticated",
        "authenticated": True,
        "session": {
            "token": token,
            "token_type": "mission-control-session",
            "expires_at": claims["exp"],
            "role": "founder",
        },
        "user": {
            "email": email,
            "role": "founder",
        },
    }


def inspect_session(payload: dict[str, Any]) -> dict[str, Any]:
    token = str(payload.get("token") or "").strip()
    claims = _verify_token(token)
    if not claims:
        return {"status": "invalid-session", "authenticated": False}
    return {
        "status": "session-valid",
        "authenticated": True,
        "user": {
            "email": claims.get("sub"),
            "role": claims.get("role"),
        },
        "expires_at": claims.get("exp"),
    }


def logout_founder(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "logged-out",
        "authenticated": False,
        "note": "Client should delete the Mission Control session token.",
    }


def require_founder(payload: dict[str, Any]) -> dict[str, Any]:
    token = str(payload.get("token") or payload.get("session_token") or "").strip()
    claims = _verify_token(token)
    if not claims or claims.get("role") != "founder":
        return {"authorized": False, "role": "anonymous"}
    return {"authorized": True, "role": "founder", "email": str(claims.get("sub") or "")}


def _sign_claims(claims: dict[str, Any]) -> str:
    encoded = json.dumps(claims, sort_keys=True, separators=(",", ":"))
    signature = hmac.new(_session_secret().encode("utf-8"), encoded.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{_b64(encoded)}.{signature}"


def _verify_token(token: str) -> dict[str, Any] | None:
    if "." not in token:
        return None
    encoded, signature = token.rsplit(".", 1)
    try:
        body = _unb64(encoded)
    except ValueError:
        return None
    expected = hmac.new(_session_secret().encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        claims = json.loads(body)
    except json.JSONDecodeError:
        return None
    expires = str(claims.get("exp") or "")
    try:
        expires_at = datetime.fromisoformat(expires)
    except ValueError:
        return None
    if expires_at < datetime.now(timezone.utc):
        return None
    return claims


def _b64(value: str) -> str:
    import base64

    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def _unb64(value: str) -> str:
    import base64

    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii")).decode("utf-8")


def _founder_email() -> str:
    return os.getenv(FOUNDER_EMAIL_ENV, DEFAULT_FOUNDER_EMAIL)


def _password_configured() -> bool:
    return bool(os.getenv(FOUNDER_PASSWORD_ENV))


def _session_secret() -> str:
    return os.getenv(SESSION_SECRET_ENV) or "development-session-secret-change-me"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
