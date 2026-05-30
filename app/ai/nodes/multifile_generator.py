from app.ai.llm import llm
from app.ai.state import ProjectState
from app.ai.schemas.file_manifest_schema import FileManifest


def multifile_generator_node(state: ProjectState) -> ProjectState:
    architecture = state["architecture_plan"]

    structured_llm = llm.with_structured_output(
        FileManifest,
        method="function_calling",
    )

    prompt = f"""
You are an enterprise AI software engineer.

Generate a complete multi-file starter app.

ENTERPRISE MODULE RULES:
- Every file must be small and focused.
- Prefer many small files over one large file.
- No file should exceed 120 lines if possible.
- Split logic into schemas, models, services, routes, dependencies, and core utilities.
- Every import used must correspond to a generated file.
- Every API route used by the frontend must exist in the backend.
- Every backend response expected by the frontend must match.
- Authentication must include register, login, current user, JWT generation, JWT verification, and protected-route dependency.
- RBAC must include owner, admin, developer, viewer.
- Configuration must use environment variables only.
- Include .env.example, not real secrets.
- Include README setup instructions.
- Every generated file_path must be unique.
- Every imported module must correspond to another generated file.
- No orphan files.
- No circular imports.

ENTERPRISE AI PLATFORM REQUIREMENTS::
- LangChain for orchestration abstraction
- LangGraph for workflow orchestration
- LangSmith tracing support

Architecture:
{architecture}

STRICT STACK:
- Backend: FastAPI
- Frontend: Next.js App Router
- Database: PostgreSQL
- Auth: JWT
- Styling: Tailwind CSS

STRICT SECURITY RULES:
- no hardcoded secrets
- use environment variables
- no eval
- no exec
- no shell commands
- no unsafe file paths
- no placeholders like TODO

Required backend files:
- backend/main.py
- backend/requirements.txt
- backend/.env.example
- backend/app/__init__.py
- backend/app/core/config.py
- backend/app/core/database.py
- backend/app/core/security.py
- backend/app/api/__init__.py
- backend/app/api/dependencies.py
- backend/app/api/routes/auth.py
- backend/app/api/routes/customers.py
- backend/app/api/routes/dashboard.py
- backend/app/models/user.py
- backend/app/models/customer.py
- backend/app/models/organization.py
- backend/app/models/membership.py
- backend/app/schemas/auth.py
- backend/app/schemas/customer.py
- backend/app/services/auth_service.py
- backend/app/services/customer_service.py

Required frontend files:
- frontend/package.json
- frontend/.env.example
- frontend/app/layout.tsx
- frontend/app/page.tsx
- frontend/app/login/page.tsx
- frontend/app/register/page.tsx
- frontend/app/dashboard/page.tsx
- frontend/app/customers/page.tsx
- frontend/components/Navbar.tsx
- frontend/components/CustomerTable.tsx
- frontend/lib/api.ts
- frontend/lib/auth.ts
"""

    manifest = structured_llm.invoke(prompt)

    return {
        **state,
        "file_manifest": manifest.model_dump(),
        "current_step": "multifile_generation_completed",
    }
