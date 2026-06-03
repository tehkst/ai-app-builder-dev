import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Header, HTTPException, status


BASE_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)


PLATFORM_INTERNAL_TOKEN_HEADER = "X-Platform-Internal-Token"
PLATFORM_INTERNAL_TOKEN = os.getenv("PLATFORM_INTERNAL_TOKEN", "")


def require_platform_admin(
    x_platform_internal_token: str = Header(default="", alias=PLATFORM_INTERNAL_TOKEN_HEADER),
):
    """Internal platform API guard.

    This guard fails closed when PLATFORM_INTERNAL_TOKEN is not configured.
    Later this should be replaced with proper platform JWT/RBAC enforcement.
    """
    if not PLATFORM_INTERNAL_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Platform API token is not configured.",
        )

    if not x_platform_internal_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Platform API authentication is required.",
        )

    if x_platform_internal_token != PLATFORM_INTERNAL_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid platform API token.",
        )

    return {
        "role": "platform_admin",
        "auth_mode": "internal_token",
    }
