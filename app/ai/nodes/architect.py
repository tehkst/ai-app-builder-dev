import json
import re

from app.ai.llm import invoke_llm
from app.ai.state import ProjectState
from app.ai.schemas.architecture_schema import ArchitectureSchema


def extract_json(text: str) -> dict:
    cleaned = text.strip()

    code_block_match = re.search(
        r"```(?:json)?\s*(.*?)```",
        cleaned,
        re.DOTALL,
    )

    if code_block_match:
        cleaned = code_block_match.group(1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in LLM response: {text[:500]}")

    json_text = cleaned[start : end + 1]

    return json.loads(json_text)


def architect_node(state: ProjectState) -> ProjectState:
    prompt = f"""
You are a principal enterprise architect.

Analyze this app request:

{state["raw_prompt"]}

STRICT RULES:
- backend MUST be FastAPI
- frontend MUST be Next.js App Router
- database MUST be PostgreSQL
- auth MUST be JWT
- architecture MUST be modular enterprise architecture

Return ONLY valid JSON.
Do not include markdown.
Do not include explanation.
Do not wrap the JSON in ```json.

Required JSON structure:

{{
    "app_type": "",
    "frontend_framework": "",
    "backend_framework": "",
    "database": "",
    "authentication": "",
    "pages": [],
    "api_modules": [],
    "database_tables": [],
    "deployment_strategy": ""
}}
"""

    response = invoke_llm(
        prompt,
        node_name="architect",
        project_id=state.get("project_id"),
        metadata={
            "current_step": state.get("current_step"),
        },
    )

    architecture_data = extract_json(response.content)

    validated = ArchitectureSchema(**architecture_data)

    return {
        **state,
        "architecture_plan": validated.model_dump(),
        "current_step": "architecture_completed",
    }
