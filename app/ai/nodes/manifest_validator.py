from app.ai.state import ProjectState


REQUIRED_FILES = {
    "README.md",
    "backend/main.py",
    "backend/requirements.txt",
    "backend/.env.example",
    "backend/app/__init__.py",
    "backend/app/core/config.py",
    "backend/app/core/database.py",
    "backend/app/core/security.py",
    "backend/app/api/__init__.py",
    "backend/app/api/routes/__init__.py",
    "backend/app/api/dependencies.py",
    "backend/app/api/routes/auth.py",
    "backend/app/api/routes/customers.py",
    "backend/app/api/routes/dashboard.py",
    "backend/app/models/user.py",
    "backend/app/models/customer.py",
    "backend/app/models/organization.py",
    "backend/app/models/membership.py",
    "backend/app/schemas/auth.py",
    "backend/app/schemas/customer.py",
    "backend/app/services/auth_service.py",
    "backend/app/services/customer_service.py",
    "frontend/package.json",
    "frontend/.env.example",
    "frontend/app/layout.tsx",
    "frontend/app/page.tsx",
    "frontend/app/login/page.tsx",
    "frontend/app/register/page.tsx",
    "frontend/app/dashboard/page.tsx",
    "frontend/app/customers/page.tsx",
    "frontend/components/Navbar.tsx",
    "frontend/components/CustomerTable.tsx",
    "frontend/lib/api.ts",
    "frontend/lib/auth.ts",
}


def manifest_validator_node(state: ProjectState) -> ProjectState:
    files = state.get("file_manifest", {}).get("files", [])

    file_path_list = [
        file.get("file_path")
        for file in files
    ]

    file_paths = set(file_path_list)

    missing_files = sorted(REQUIRED_FILES - file_paths)

    duplicate_files = []

    seen = set()

    for path in file_path_list:
        if path in seen:
            duplicate_files.append(path)

        seen.add(path)

    validation_passed = not missing_files and not duplicate_files

    return {
        **state,
        "manifest_validation": {
            "passed": validation_passed,
            "missing_files": missing_files,
            "duplicate_files": duplicate_files,
        },
        "current_step": "manifest_validation_completed",
    }
