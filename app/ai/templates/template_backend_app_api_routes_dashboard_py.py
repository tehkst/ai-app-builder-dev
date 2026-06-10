from __future__ import annotations


TEMPLATE_PATH = 'backend/app/api/routes/dashboard.py'
TEMPLATE_CONTENT = 'from fastapi import APIRouter, Depends\nfrom sqlalchemy import func, select\nfrom sqlalchemy.ext.asyncio import AsyncSession\n\nfrom app.api.dependencies import get_current_user_id, require_role\nfrom app.core.database import get_db\nfrom app.models.customer import Customer\n\n\nrouter = APIRouter()\n\n\n@router.get("/summary")\nasync def dashboard_summary(\n    current_user_id: str = Depends(get_current_user_id),\n    _: bool = Depends(require_role(["owner", "admin", "member", "viewer"])),\n    db: AsyncSession = Depends(get_db),\n):\n    result = await db.execute(\n        select(func.count(Customer.id))\n    )\n\n    customer_count = result.scalar_one()\n\n    return {\n        "customer_count": customer_count,\n        "current_user_id": current_user_id,\n    }\n'
