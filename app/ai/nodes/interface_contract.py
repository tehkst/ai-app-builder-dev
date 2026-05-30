from app.ai.llm import llm
from app.ai.state import ProjectState
from app.ai.schemas.interface_contract_schema import InterfaceContract


def interface_contract_node(state: ProjectState) -> ProjectState:
    file_plan = state.get("file_plan", {})

    structured_llm = llm.with_structured_output(
        InterfaceContract,
        method="function_calling",
    )

    prompt = f"""
You are an enterprise software architect.

Create a strict interface contract for this file plan.

File plan:
{file_plan}

Rules:
- Every imported function/class must be exported by exactly one file.
- Authentication must define:
  - create_access_token
  - decode_access_token
  - hash_password
  - verify_password
  - authenticate_user
  - get_current_user
  - require_role must be exported from backend/app/api/dependencies.py
- Models must define:
  - User
  - Customer
  - Organization
  - Membership
- RBAC must define:
  - role constants may be implemented in backend/app/models/membership.py
  - RBAC must use require_role from backend/app/api/dependencies.py
  - Do not invent check_permission or permission_check
  - Do not import Role from app.core.security
- API endpoints must include:
  - POST /api/auth/register
  - POST /api/auth/login
  - GET /api/auth/me
  - GET /api/customers
  - POST /api/customers
  - GET /api/dashboard/summary
"""

    contract = structured_llm.invoke(prompt)

    return {
        **state,
        "interface_contract": contract.model_dump(),
        "current_step": "interface_contract_created",
    }
