from __future__ import annotations

from typing import Dict

from app.platform.auth.auth_models import Identity


def identity_registry() -> Dict[str, Identity]:
    identity = Identity(
        user_id="user_platform_owner",
        email="platform.owner@example.com",
        display_name="Platform Owner",
    )
    return {identity.user_id: identity}


def find_identity(user_id: str) -> Identity:
    return identity_registry()[user_id]
