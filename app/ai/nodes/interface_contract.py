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
- Authentication and security exports must include exactly:
  - backend/app/core/security.py exports:
    - create_access_token
    - decode_access_token
    - hash_password
    - verify_password
  - backend/app/api/dependencies.py exports:
    - get_current_user_id
    - get_current_user
    - require_role
  - backend/app/services/auth_service.py exports:
    - get_user_by_email
    - get_user_by_username
    - create_user
    - authenticate_user
- Models must define:
  - User
  - Customer
  - Organization
  - Membership
- RBAC must define:
  - require_role must be exported from backend/app/api/dependencies.py
  - get_current_user_id must be exported from backend/app/api/dependencies.py
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
