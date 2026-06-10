from __future__ import annotations


TEMPLATE_PATH = 'backend/app/models/customer.py'
TEMPLATE_CONTENT = 'from sqlalchemy import Column, Integer, String\n\nfrom app.core.database import Base\n\n\nclass Customer(Base):\n    __tablename__ = "customers"\n\n    id = Column(Integer, primary_key=True, index=True)\n    name = Column(String, index=True, nullable=False)\n    email = Column(String, unique=True, index=True, nullable=True)\n    phone = Column(String, nullable=True)\n    company = Column(String, nullable=True)\n'
