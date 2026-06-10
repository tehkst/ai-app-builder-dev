from __future__ import annotations


TEMPLATE_PATH = 'backend/app/models/membership.py'
TEMPLATE_CONTENT = 'from sqlalchemy import Column, Integer, String\n\nfrom app.core.database import Base\n\n\nclass Membership(Base):\n    __tablename__ = "memberships"\n\n    id = Column(Integer, primary_key=True, index=True)\n    user_id = Column(Integer, index=True, nullable=False)\n    organization_id = Column(Integer, index=True, nullable=False)\n    role = Column(String, default="member", nullable=False)\n'
