from app.ai.state import ProjectState


REQUIRED_FILE_PLAN = [
    {
        "file_path": "README.md",
        "file_type": "markdown",
        "purpose": "Project overview and setup instructions",
    },
    {
        "file_path": "backend/main.py",
        "file_type": "python",
        "purpose": "FastAPI application entrypoint",
    },
    {
        "file_path": "backend/requirements.txt",
        "file_type": "text",
        "purpose": "Backend Python dependencies",
    },
    {
        "file_path": "backend/.env.example",
        "file_type": "env",
        "purpose": "Backend environment variable template",
    },
    {
        "file_path": "backend/app/__init__.py",
        "file_type": "python",
        "purpose": "Backend app package initializer",
    },
    {
        "file_path": "backend/app/core/config.py",
        "file_type": "python",
        "purpose": "Application settings and environment configuration",
    },
    {
        "file_path": "backend/app/core/database.py",
        "file_type": "python",
        "purpose": "Database engine, session, Base, and get_db dependency",
    },
    {
        "file_path": "backend/app/core/security.py",
        "file_type": "python",
        "purpose": "Password hashing and JWT token utilities",
    },
    {
        "file_path": "backend/app/api/__init__.py",
        "file_type": "python",
        "purpose": "API package initializer",
    },
    {
        "file_path": "backend/app/api/dependencies.py",
        "file_type": "python",
        "purpose": "Authentication and RBAC dependencies",
    },
    {
        "file_path": "backend/app/api/routes/__init__.py",
        "file_type": "python",
        "purpose": "Route module exports",
    },
    {
        "file_path": "backend/app/api/routes/auth.py",
        "file_type": "python",
        "purpose": "Authentication API routes",
    },
    {
        "file_path": "backend/app/api/routes/customers.py",
        "file_type": "python",
        "purpose": "Customer API routes",
    },
    {
        "file_path": "backend/app/api/routes/dashboard.py",
        "file_type": "python",
        "purpose": "Dashboard API routes",
    },
    {
        "file_path": "backend/app/models/user.py",
        "file_type": "python",
        "purpose": "User database model",
    },
    {
        "file_path": "backend/app/models/customer.py",
        "file_type": "python",
        "purpose": "Customer database model",
    },
    {
        "file_path": "backend/app/models/organization.py",
        "file_type": "python",
        "purpose": "Organization database model",
    },
    {
        "file_path": "backend/app/models/membership.py",
        "file_type": "python",
        "purpose": "Membership and role database model",
    },
    {
        "file_path": "backend/app/schemas/auth.py",
        "file_type": "python",
        "purpose": "Pydantic authentication request and response schemas",
    },
    {
        "file_path": "backend/app/schemas/customer.py",
        "file_type": "python",
        "purpose": "Pydantic customer request and response schemas",
    },
    {
        "file_path": "backend/app/services/auth_service.py",
        "file_type": "python",
        "purpose": "Authentication business logic",
    },
    {
        "file_path": "backend/app/services/customer_service.py",
        "file_type": "python",
        "purpose": "Customer business logic",
    },
    {
        "file_path": "frontend/package.json",
        "file_type": "json",
        "purpose": "Frontend dependencies and scripts",
    },
    {
        "file_path": "frontend/.env.example",
        "file_type": "env",
        "purpose": "Frontend environment variable template",
    },
    {
        "file_path": "frontend/app/layout.tsx",
        "file_type": "typescript",
        "purpose": "Next.js root layout",
    },
    {
        "file_path": "frontend/app/page.tsx",
        "file_type": "typescript",
        "purpose": "Landing page",
    },
    {
        "file_path": "frontend/app/login/page.tsx",
        "file_type": "typescript",
        "purpose": "Login page",
    },
    {
        "file_path": "frontend/app/register/page.tsx",
        "file_type": "typescript",
        "purpose": "Registration page",
    },
    {
        "file_path": "frontend/app/dashboard/page.tsx",
        "file_type": "typescript",
        "purpose": "Dashboard page",
    },
    {
        "file_path": "frontend/app/customers/page.tsx",
        "file_type": "typescript",
        "purpose": "Customer management page",
    },
    {
        "file_path": "frontend/components/Navbar.tsx",
        "file_type": "typescript",
        "purpose": "Navigation component",
    },
    {
        "file_path": "frontend/components/CustomerTable.tsx",
        "file_type": "typescript",
        "purpose": "Customer table component",
    },
    {
        "file_path": "frontend/lib/api.ts",
        "file_type": "typescript",
        "purpose": "Frontend API client",
    },
    {
        "file_path": "frontend/lib/auth.ts",
        "file_type": "typescript",
        "purpose": "Frontend authentication helpers",
    },
]


def manifest_generator_node(state: ProjectState) -> ProjectState:
    return {
        **state,
        "file_plan": {
            "files": REQUIRED_FILE_PLAN,
        },
        "current_step": "file_plan_created",
    }
