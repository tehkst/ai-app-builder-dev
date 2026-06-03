import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Header, HTTPException, Request, status

from app.platform.persistence.audit import create_audit_event
from app.platform.persistence.database import PlatformSessionLocal


BASE_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)


PLATFORM_INTERNAL_TOKEN_HEADER = "X-Platform-Internal-Token"
PLATFORM_INTERNAL_TOKEN = os.getenv("PLATFORM_INTERNAL_TOKEN", "")


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


def require_platform_admin(
    request: Request,
    x_platform_internal_token: str = Header(default="", alias=PLATFORM_INTERNAL_TOKEN_HEADER),
):
    """Internal platform API guard.

    This guard fails closed when PLATFORM_INTERNAL_TOKEN is not configured.
    Later this should be replaced with proper platform JWT/RBAC enforcement.
    """
    route = str(request.url.path)

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
            auth_mode="internal_token",
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

    return {
        "role": "platform_admin",
        "auth_mode": "internal_token",
    }
