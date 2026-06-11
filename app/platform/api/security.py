import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Header, HTTPException, Request, status
from jose import JWTError

from app.core.security import create_access_token, decode_access_token
from app.platform.api.security_config import internal_token_fallback_allowed
from app.platform.persistence.audit import create_audit_event
from app.platform.persistence.database import PlatformSessionLocal


BASE_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)


PLATFORM_INTERNAL_TOKEN_HEADER = "X-Platform-Internal-Token"
PLATFORM_INTERNAL_TOKEN = os.getenv("PLATFORM_INTERNAL_TOKEN", "")
PLATFORM_ADMIN_USERNAME = os.getenv("PLATFORM_ADMIN_USERNAME", "")
PLATFORM_ADMIN_PASSWORD = os.getenv("PLATFORM_ADMIN_PASSWORD", "")
PLATFORM_ADMIN_JWT_SUBJECT = "platform_admin"


def record_platform_auth_audit(
    *,
    event_type: str,
    status_value: str,
    route: Optional[str] = None,
    auth_mode: Optional[str] = None,
):
    db = PlatformSessionLocal()

    try:
        create_audit_event(
            db,
            event_type=event_type,
            status=status_value,
            actor_type="platform_admin",
            route=route,
            auth_mode=auth_mode,
        )
    finally:
        db.close()


def platform_admin_login(*, username: str, password: str, route: str = "/platform/auth/login") -> dict:
    if not PLATFORM_ADMIN_USERNAME or not PLATFORM_ADMIN_PASSWORD:
        record_platform_auth_audit(
            event_type="platform_admin_login_not_configured",
            status_value="failure",
            route=route,
            auth_mode="jwt_admin_login",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Platform admin login is not configured.",
        )

    if username != PLATFORM_ADMIN_USERNAME or password != PLATFORM_ADMIN_PASSWORD:
        record_platform_auth_audit(
            event_type="platform_admin_login_invalid",
            status_value="failure",
            route=route,
            auth_mode="jwt_admin_login",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid platform admin credentials.",
        )

    token = create_access_token(subject=PLATFORM_ADMIN_JWT_SUBJECT)
    record_platform_auth_audit(
        event_type="platform_admin_login_success",
        status_value="success",
        route=route,
        auth_mode="jwt_admin_login",
    )
    return {"access_token": token, "token_type": "bearer", "role": "platform_admin", "auth_mode": "jwt_admin_login"}


def _authorize_with_bearer_token(*, bearer_token: str, route: str) -> Optional[dict]:
    if not bearer_token:
        return None

    try:
        payload = decode_access_token(bearer_token)
    except JWTError:
        record_platform_auth_audit(
            event_type="platform_api_jwt_invalid",
            status_value="failure",
            route=route,
            auth_mode="jwt_bearer",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid platform admin JWT.",
        )

    if payload.get("sub") != PLATFORM_ADMIN_JWT_SUBJECT:
        record_platform_auth_audit(
            event_type="platform_api_jwt_wrong_subject",
            status_value="failure",
            route=route,
            auth_mode="jwt_bearer",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid platform admin JWT subject.",
        )

    record_platform_auth_audit(
        event_type="platform_api_jwt_success",
        status_value="success",
        route=route,
        auth_mode="jwt_bearer",
    )
    return {"role": "platform_admin", "auth_mode": "jwt_bearer", "subject": payload.get("sub")}


def require_platform_admin(
    request: Request,
    x_platform_internal_token: str = Header(default="", alias=PLATFORM_INTERNAL_TOKEN_HEADER),
    authorization: str = Header(default="", alias="Authorization"),
):
    """Require platform admin JWT; internal token is a controlled fallback."""
    route = str(request.url.path)

    if authorization.lower().startswith("bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()
        return _authorize_with_bearer_token(bearer_token=bearer_token, route=route)

    if not internal_token_fallback_allowed():
        record_platform_auth_audit(
            event_type="platform_api_internal_token_disabled",
            status_value="failure",
            route=route,
            auth_mode="internal_token",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Platform admin JWT is required in this environment.",
        )

    if not PLATFORM_INTERNAL_TOKEN:
        record_platform_auth_audit(
            event_type="platform_api_token_not_configured",
            status_value="failure",
            route=route,
            auth_mode="internal_token",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Platform API token is not configured.",
        )

    if not x_platform_internal_token:
        record_platform_auth_audit(
            event_type="platform_api_auth_missing",
            status_value="failure",
            route=route,
            auth_mode="platform_admin_gate",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Platform API authentication is required.",
        )

    if x_platform_internal_token != PLATFORM_INTERNAL_TOKEN:
        record_platform_auth_audit(
            event_type="platform_api_auth_invalid",
            status_value="failure",
            route=route,
            auth_mode="internal_token",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid platform API token.",
        )

    record_platform_auth_audit(
        event_type="platform_api_auth_success",
        status_value="success",
        route=route,
        auth_mode="internal_token",
    )

    return {"role": "platform_admin", "auth_mode": "internal_token"}
