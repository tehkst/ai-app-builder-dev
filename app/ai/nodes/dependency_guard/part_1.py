# Split from the legacy module to keep each Python file under 200 lines.
import re
from app.ai.state import ProjectState
STRONG_EXPORTS = {
    "backend/app/core/config.py": [
        "settings",
    ],
    "backend/app/core/database.py": [
        "Base",
        "engine",
        "AsyncSessionLocal",
        "get_db",
    ],
    "backend/app/core/security.py": [
        "hash_password",
        "verify_password",
        "create_access_token",
        "decode_access_token",
    ],
    "backend/app/api/dependencies.py": [
        "get_current_user",
        "get_current_user_id",
        "require_role",
    ],
    "backend/app/api/routes/__init__.py": [
        "auth",
        "customers",
        "dashboard",
    ],
    "backend/app/api/__init__.py": [],
    "backend/app/models/user.py": [
        "User",
    ],
    "backend/app/models/customer.py": [
        "Customer",
    ],
    "backend/app/models/organization.py": [
        "Organization",
    ],
    "backend/app/models/membership.py": [
        "Membership",
    ],
    "backend/app/services/auth_service.py": [
        "get_user_by_email",
        "get_user_by_username",
        "create_user",
        "authenticate_user",
    ],
    "backend/app/services/customer_service.py": [
        "create_customer",
        "get_customers",
    ],
}
FORBIDDEN_MODULES = {
    "app.security": "Use app.core.security instead of app.security",
}
FORBIDDEN_SYMBOLS = {
    "permission_check": "Use require_role instead of permission_check",
    "check_permission": "Use require_role instead of check_permission",
    "SessionLocal": "Use get_db instead of importing SessionLocal directly",
}

def module_to_file_path(module_name: str) -> str:
    if not module_name.startswith("app."):
        return ""

    if module_name == "app.api.routes":
        return "backend/app/api/routes/__init__.py"

    if module_name == "app.api":
        return "backend/app/api/__init__.py"

    parts = module_name.split(".")
    return "backend/" + "/".join(parts) + ".py"

def extract_imports(content: str):
    imports = []

    for line in content.splitlines():
        line = line.strip()

        match = re.match(
            r"from\s+(app\.[\w\.]+)\s+import\s+(.+)",
            line,
        )

        if match:
            module_name = match.group(1)
            raw_symbols = match.group(2).split(",")

            symbols = [
                symbol.strip().split(" as ")[0]
                for symbol in raw_symbols
            ]

            imports.append(
                {
                    "module": module_name,
                    "symbols": symbols,
                }
            )

    return imports
