from __future__ import annotations


TEMPLATE_PATH = 'backend/app/api/routes/__init__.py'
TEMPLATE_CONTENT = 'from app.api.routes import auth, customers, dashboard\n\n__all__ = [\n    "auth",\n    "customers",\n    "dashboard",\n]\n'
