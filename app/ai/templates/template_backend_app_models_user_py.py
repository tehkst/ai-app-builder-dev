from __future__ import annotations


TEMPLATE_PATH = 'backend/app/models/user.py'
TEMPLATE_CONTENT = 'from sqlalchemy import Boolean, Column, Integer, String\n\nfrom app.core.database import Base\n\n\nclass User(Base):\n    __tablename__ = "users"\n\n    id = Column(Integer, primary_key=True, index=True)\n    username = Column(String, unique=True, index=True, nullable=False)\n    email = Column(String, unique=True, index=True, nullable=False)\n    hashed_password = Column(String, nullable=False)\n    is_active = Column(Boolean, default=True, nullable=False)\n'
