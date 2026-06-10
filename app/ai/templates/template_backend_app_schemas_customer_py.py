from __future__ import annotations


TEMPLATE_PATH = 'backend/app/schemas/customer.py'
TEMPLATE_CONTENT = 'from typing import Optional\n\nfrom pydantic import BaseModel, EmailStr\n\n\nclass CustomerCreate(BaseModel):\n    name: str\n    email: Optional[EmailStr] = None\n    phone: Optional[str] = None\n    company: Optional[str] = None\n\n\nclass CustomerResponse(BaseModel):\n    id: int\n    name: str\n    email: Optional[EmailStr] = None\n    phone: Optional[str] = None\n    company: Optional[str] = None\n\n    class Config:\n        from_attributes = True\n'
