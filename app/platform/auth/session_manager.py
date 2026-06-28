from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    user_id: str
    tenant_id: str
    active: bool = True


def create_session(session_id: str, user_id: str, tenant_id: str) -> SessionRecord:
    return SessionRecord(session_id=session_id, user_id=user_id, tenant_id=tenant_id)


def session_is_active(session: SessionRecord) -> bool:
    return session.active
