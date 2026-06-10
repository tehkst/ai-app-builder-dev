from __future__ import annotations


TEMPLATE_PATH = 'backend/app/models/organization.py'
TEMPLATE_CONTENT = 'from sqlalchemy import Column, Integer, String\n\nfrom app.core.database import Base\n\n\nclass Organization(Base):\n    __tablename__ = "organizations"\n\n    id = Column(Integer, primary_key=True, index=True)\n    name = Column(String, unique=True, index=True, nullable=False)\n'
