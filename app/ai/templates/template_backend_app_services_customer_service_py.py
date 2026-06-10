from __future__ import annotations


TEMPLATE_PATH = 'backend/app/services/customer_service.py'
TEMPLATE_CONTENT = 'from sqlalchemy import select\nfrom sqlalchemy.ext.asyncio import AsyncSession\n\nfrom app.models.customer import Customer\nfrom app.schemas.customer import CustomerCreate\n\n\nasync def get_customers(\n    db: AsyncSession,\n):\n    result = await db.execute(\n        select(Customer)\n    )\n\n    return result.scalars().all()\n\n\nasync def create_customer(\n    db: AsyncSession,\n    payload: CustomerCreate,\n):\n    customer = Customer(**payload.model_dump())\n\n    db.add(customer)\n    await db.commit()\n    await db.refresh(customer)\n\n    return customer\n'
