import re

from app.ai.state import ProjectState


STRONG_EXPORTS = {
    "backend/app/core/config.py": [
        "settings",
    ],
    "backend/app/core/database.py": [
        "Base",
        "engine",
        "AsynSessionLocal",
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
        "got_user_by_username",
        "create_user",
        "authenticate_user",
        "get_current_user",
    ],
    "backend/app/services/customer_service.py": [
        "create_customer",
        "get_customers",
        "update_customer",
        "get_customer_by_id",
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


def dependency_guard_node(state: ProjectState) -> ProjectState:
    files = state.get("file_manifest", {}).get("files", [])

    file_map = {
        file.get("file_path"): file.get("content", "")
        for file in files
    }

    issues = []

    for consumer_path, content in file_map.items():
        imports = extract_imports(content)

        for import_item in imports:
            module_name = import_item["module"]

            if module_name in FORBIDDEN_MODULES:
                issues.append(
                    {
                        "severity": "high",
                        "dependency_type": "forbidden_import",
                        "producer": module_to_file_path(module_name),
                        "consumer": consumer_path,
                        "issue": FORBIDDEN_MODULES[module_name],
                    }
                )
                continue

            producer_path = module_to_file_path(module_name)

            if not producer_path:
                continue

            if producer_path not in file_map:
                issues.append(
                    {
                        "severity": "high",
                        "dependency_type": "strong_import",
                        "producer": producer_path,
                        "consumer": consumer_path,
                        "issue": "Producer module missing from file manifest",
                    }
                )
                continue

            expected_exports = STRONG_EXPORTS.get(producer_path)

            if expected_exports is not None:
                for symbol in import_item["symbols"]:

                    if symbol in FORBIDDEN_SYMBOLS:
                        issues.append(
                            {
                                "severity": "high",
                                "dependency_type": "forbidden_symbol",
                                "producer": producer_path,
                                "consumer": consumer_path,
                                "issue": FORBIDDEN_SYMBOLS[symbol],
                            }
                        )
                        continue

                    if (
                        producer_path == "backend/app/services/auth_service.py"
                        and symbol == "create_access_token"
                    ):
                        issues.append(
                            {
                                "severity": "high",
                                "dependency_type": "forbidden_symbol",
                                "producer": producer_path,
                                "consumer": consumer_path,
                                "issue": "create_access_token must be imported from app.core.security, not auth_service",
                            }
                        )
                        continue

                    if (
                        producer_path == "backend/app/core/config.py"
                        and symbol == "DATABASE_URL"
                    ):
                        issues.append(
                            {
                                "severity": "high",
                                "dependency_type": "forbidden_symbol",
                                "producer": producer_path,
                                "consumer": consumer_path,
                                "issue": "Use settings.DATABASE_URL instead of importing DATABASE_URL directly",
                            }
                        )
                        continue

                    if expected_exports and symbol not in expected_exports:
                        issues.append(
                            {
                                "severity": "high",
                                "dependency_type": "strong_symbol",
                                "producer": producer_path,
                                "consumer": consumer_path,
                                "issue": f"Symbol '{symbol}' is not listed as exported by producer",
                            }
                        )

    return {
        **state,
        "dependency_report": {
            "passed": len(issues) == 0,
            "issues": issues,
        },
        "current_step": "dependency_guard_completed",
    }
