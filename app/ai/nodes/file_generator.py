from app.ai.llm import invoke_llm
from app.ai.state import ProjectState


def file_generator_node(state: ProjectState) -> ProjectState:
    file_plan = state.get("file_plan", {}).get("files", [])
    architecture = state["architecture_plan"]
    interface_contract = state.get("interface_contract", {})
    full_file_plan = state.get("file_plan", {})

    generated_files = []

    for item in file_plan:
        file_path = item["file_path"]
        file_type = item["file_type"]
        purpose = item["purpose"]

        prompt = f"""
You are an enterprise software engineer.

Generate ONLY the content for this file.

Full file plan:
{full_file_plan}

Interface contract:
{interface_contract}

File path:
{file_path}

File type:
{file_type}

Purpose:
{purpose}

Architecture:
{architecture}

STRICT RULES:
- Return only file content.
- No markdown fences.
- No explanations.
- No hardcoded secrets.
- Use environment variables.
- Keep file small and focused.
- No TODO placeholders.
- Every import must match the file plan and interface contract.
- You may only import symbols listed in the interface contract.
- If this file exports symbols, they must match the interface contract.
- Backend API routes must match the interface contract exactly.
- Never import from app.security.
- Security utilities must only be imported from app.core.security.
- Config must only be imported from app.core.config.
- Database must only be imported from app.core.database.
- Never import permission_check.
- Use require_role from app.api.dependencies for RBAC checks.
- Never import SessionLocal directly.
- Use get_db from app.core.database with FastAPI Depends.
- Never import create_access_token from app.services.auth_service.
- create_access_token must only be imported from app.core.security.
- Never import DATABASE_URL from app.core.config.
- Database configuration must use settings.DATABASE_URL from app.core.config.
"""

        response = invoke_llm(prompt)

        generated_files.append(
            {
                "file_path": file_path,
                "file_type": file_type,
                "purpose": purpose,
                "content": response.content.strip(),
            }
        )

    return {
        **state,
        "file_manifest": {
            "files": generated_files,
        },
        "current_step": "files_generated",
    }
