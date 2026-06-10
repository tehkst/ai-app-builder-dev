from __future__ import annotations


TEMPLATE_PATH = 'backend/app/models/audit_log.py'
TEMPLATE_CONTENT = 'from datetime import datetime, timezone\n\nfrom sqlalchemy import Column, DateTime, Integer, String, Text\n\nfrom app.core.database import Base\n\n\nclass AuditLog(Base):\n    __tablename__ = "audit_logs"\n\n    id = Column(Integer, primary_key=True, index=True)\n    event_type = Column(String, index=True, nullable=False)\n    status = Column(String, index=True, nullable=False)\n    actor_user_id = Column(Integer, index=True, nullable=True)\n    route = Column(String, nullable=True)\n    detail = Column(Text, nullable=True)\n    created_at = Column(\n        DateTime(timezone=True),\n        default=lambda: datetime.now(timezone.utc),\n        nullable=False,\n    )\n'
