from fastapi import Header, HTTPException, status


PLATFORM_INTERNAL_TOKEN_HEADER = "X-Platform-Internal-Token"


def require_platform_admin(
    x_platform_internal_token: str = Header(default="", alias=PLATFORM_INTERNAL_TOKEN_HEADER),
):
    """Temporary platform API guard.

    This is intentionally strict by default. Until real platform JWT/RBAC is wired,
    callers must provide an internal token configured through deployment settings.
    """
    if not x_platform_internal_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Platform API authentication is required.",
        )

    return {
        "role": "platform_admin",
        "auth_mode": "internal_token_placeholder",
    }
