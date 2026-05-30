import json

from app.ai.llm import invoke_llm
from app.ai.state import ProjectState


def code_generator_node(state: ProjectState) -> ProjectState:

    architecture = json.dumps(
        state["architecture_plan"],
        indent=2,
    )

    backend_prompt = f"""
Generate production-ready FastAPI backend code.

Architecture:
{architecture}

STRICT RULES:
- FastAPI only
- async APIs
- PostgreSQL
- SQLAlchemy
- JWT auth
- modular architecture
- environment variables only
- no hardcoded secrets
- production-ready structure

Return ONLY backend code.
"""

    frontend_prompt = f"""
Generate production-ready Next.js App Router frontend code.

Architecture:
{architecture}

STRICT RULES:
- Next.js App Router
- Tailwind CSS
- JWT auth integration
- responsive dashboard
- no placeholder comments
- production-ready structure

Return ONLY frontend code.
"""

    backend_response = invoke_llm(backend_prompt)

    frontend_response = invoke_llm(frontend_prompt)

    return {
        **state,

        "generated_backend_code": backend_response.content,

        "generated_frontend_code": frontend_response.content,

        "current_step": "code_generation_completed",
    }
