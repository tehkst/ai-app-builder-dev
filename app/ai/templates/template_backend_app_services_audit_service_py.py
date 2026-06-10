from __future__ import annotations


TEMPLATE_PATH = 'backend/app/services/audit_service.py'
TEMPLATE_CONTENT = 'from typing import Optional\n\nfrom sqlalchemy.ext.asyncio import AsyncSession\n\nfrom app.models.audit_log import AuditLog\n\n\nasync def create_audit_log(\n    db: AsyncSession,\n    event_type: str,\n    status: str,\n    actor_user_id: Optional[int] = None,\n    route: Optional[str] = None,\n    detail: Optional[str] = None,\n) -> AuditLog:\n    audit_log = AuditLog(\n        event_type=event_type,\n        status=status,\n        actor_user_id=actor_user_id,\n        route=route,\n        detail=detail,\n    )\n\n    db.add(audit_log)\n    await db.commit()\n    await db.refresh(audit_log)\n\n    return audit_log\n'
