from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

FOUNDER_EMAIL_ENV = "FOUNDER_EMAIL"
FOUNDER_PASSWORD_ENV = "FOUNDER_PASSWORD"
SESSION_SECRET_ENV = "MISSION_CONTROL_SESSION_SECRET"
DEFAULT_FOUNDER_EMAIL = "founder@ai-software-factory.local"
RESET_TOKEN_TTL_MINUTES = 30
SESSION_IDLE_HOURS = 12  # a session lasts this long without Mission Control open to renew it
SESSION_MAX_DAYS = 7  # then the password is asked again, however often it was renewed


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

    if email != expected_email:
        return {
            "status": "invalid-credentials",
            "authenticated": False,
        }

    persisted_hash = _persisted_password_hash()
    if persisted_hash:
        from app.core.security import verify_password

        if not password or not verify_password(password, persisted_hash):
            return {
                "status": "invalid-credentials",
                "authenticated": False,
            }
    else:
        expected_password = os.getenv(FOUNDER_PASSWORD_ENV)
        if not expected_password:
            return {
                "status": "blocked-missing-founder-password",
                "authenticated": False,
                "secret_name": FOUNDER_PASSWORD_ENV,
                "next_step": "Create FOUNDER_PASSWORD in Secret Manager and mount it into Cloud Run.",
            }
        if not hmac.compare_digest(password, expected_password):
            return {
                "status": "invalid-credentials",
                "authenticated": False,
            }

    return _session_response(email, _now())


def _session_response(email: str, signed_in_at: str) -> dict[str, Any]:
    """A founder session: valid SESSION_IDLE_HOURS from now, never past SESSION_MAX_DAYS after the
    password was entered (`auth_time`)."""
    now = datetime.now(timezone.utc)
    cap = datetime.fromisoformat(signed_in_at) + timedelta(days=SESSION_MAX_DAYS)
    expires_at = min(now + timedelta(hours=SESSION_IDLE_HOURS), cap)
    claims = {
        "sub": email,
        "role": "founder",
        "iat": now.replace(microsecond=0).isoformat(),
        "auth_time": signed_in_at,
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


def refresh_session(payload: dict[str, Any]) -> dict[str, Any]:
    """A fresh token for a valid founder session, so an open Mission Control isn't signed out every
    SESSION_IDLE_HOURS; the password is asked again SESSION_MAX_DAYS after it was entered."""
    claims = _verify_token(str(payload.get("token") or "").strip())
    if not claims or claims.get("role") != "founder":
        return {"status": "invalid-session", "authenticated": False}
    signed_in_at = str(claims.get("auth_time") or claims.get("iat") or "")
    try:
        if datetime.fromisoformat(signed_in_at) + timedelta(days=SESSION_MAX_DAYS) <= datetime.now(timezone.utc):
            return {"status": "invalid-session", "authenticated": False, "error": "Sign in again."}
    except ValueError:
        return {"status": "invalid-session", "authenticated": False}
    return _session_response(str(claims.get("sub") or ""), signed_in_at)


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


def request_founder_password_reset(payload: dict[str, Any]) -> dict[str, Any]:
    from app.core.email import send_email
    from app.platform.persistence.database import PlatformSessionLocal
    from app.platform.persistence.models import PlatformFounderResetToken

    email = str(payload.get("email") or "").strip().lower()
    generic_response = {
        "status": "ok",
        "message": "If that email matches the platform admin account, a reset link has been sent.",
    }
    if email != _founder_email().lower():
        return generic_response

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
    db = PlatformSessionLocal()
    try:
        db.add(
            PlatformFounderResetToken(
                token_hash=_hash_reset_token(token),
                email=email,
                expires_at=expires_at,
            )
        )
        db.commit()
    finally:
        db.close()

    base_url = str(payload.get("_base_url") or os.getenv("PUBLIC_BASE_URL", "")).rstrip("/")
    link = f"{base_url}/reset-password?token={token}&type=founder"
    send_email(
        email,
        "Reset your AI Software Factory platform admin password",
        f"A password reset was requested for the platform admin account.\n\n"
        f"Reset your password (expires in {RESET_TOKEN_TTL_MINUTES} minutes):\n{link}\n\n"
        f"If you did not request this, you can ignore this email.",
    )
    return generic_response


def reset_founder_password(payload: dict[str, Any]) -> dict[str, Any]:
    from app.core.security import hash_password
    from app.platform.persistence.database import PlatformSessionLocal
    from app.platform.persistence.models import PlatformFounderResetToken
    from app.platform.runtime.settings_store import FOUNDER_PASSWORD_HASH_KEY, set_setting

    token = str(payload.get("token") or "").strip()
    new_password = str(payload.get("new_password") or "")
    if len(new_password) < 8:
        return {"status": "invalid-request", "error": "Password must be at least 8 characters."}

    token_hash = _hash_reset_token(token)
    db = PlatformSessionLocal()
    try:
        reset_token = db.query(PlatformFounderResetToken).filter(
            PlatformFounderResetToken.token_hash == token_hash
        ).first()
        now = datetime.now(timezone.utc)
        if not reset_token or reset_token.used_at is not None or _as_utc(reset_token.expires_at) < now:
            return {"status": "invalid-request", "error": "This reset link is invalid or has expired."}
        reset_token.used_at = now
        db.commit()
    finally:
        db.close()

    set_setting(FOUNDER_PASSWORD_HASH_KEY, hash_password(new_password))
    return {"status": "ok", "message": "Password updated. You can now sign in."}


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _persisted_password_hash() -> str | None:
    from app.platform.runtime.settings_store import FOUNDER_PASSWORD_HASH_KEY, get_setting

    return get_setting(FOUNDER_PASSWORD_HASH_KEY)


def issue_system_governance_token(reason: str) -> str:
    """Mint a short-lived, real founder-role session token for a specific, narrow, trusted
    server-side action - NOT customer-facing, never returned over HTTP. Used only where
    server code has already independently verified the caller owns the resource being acted
    on (e.g. saas_builder's customer self-service project teardown) and needs to satisfy an
    approved_cloud_run.py governance gate that otherwise requires a real founder session, so
    that gate's exact-approval-phrase/live_execution checks and audit evidence still apply
    uniformly regardless of who ultimately triggered the action.
    """
    issued_at = _now()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=2)
    claims = {
        "sub": "system:%s" % reason,
        "role": "founder",
        "iat": issued_at,
        "exp": expires_at.replace(microsecond=0).isoformat(),
    }
    return _sign_claims(claims)


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
