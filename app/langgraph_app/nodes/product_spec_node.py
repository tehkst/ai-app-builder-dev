from langchain_core.messages import SystemMessage, HumanMessage

from app.core.llm import get_llm
from app.core.llm_security import (
    scan_user_prompt,
    build_secure_system_prompt,
)
from app.langgraph_app.state import AppBuilderState
from app.schemas.product_spec import ProductSpec


async def product_spec_node(state: AppBuilderState) -> AppBuilderState:
    raw_prompt = state.get("raw_prompt", "")

    security_scan = scan_user_prompt(raw_prompt)

    if not security_scan["safe"]:
        state["product_spec"] = {
            "app_name": "Unsafe Request Blocked",
            "summary": "The request was flagged by the LLM security guardrail.",
            "target_users": [],
            "user_roles": [],
            "core_features": [],
            "pages": [],
            "database_entities": [],
            "api_modules": [],
            "non_functional_requirements": {},
            "security_requirements": [],
            "assumptions": [],
            "risks": [
                f"Suspicious prompt patterns detected: {security_scan['findings']}"
            ],
            "clarification_questions": [
                "Please rewrite the request without unsafe instructions."
            ],
        }

        state["approval_required"] = True
        state["approval_type"] = "blocked_product_spec"
        state["approved"] = False
        state["current_step"] = "product_spec_blocked_by_security"

        return state

    llm = get_llm()
    structured_llm = llm.with_structured_output(ProductSpec)

    system_prompt = build_secure_system_prompt()

    user_prompt = f"""
Create a product specification for this app idea:

{raw_prompt}

The product spec must be suitable for:
- enterprise-grade architecture
- no-code app generation
- startup MVP users
- cybersecurity review
- future QA automation
"""

    product_spec = await structured_llm.ainvoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )

    state["product_spec"] = product_spec.model_dump()
    state["approval_required"] = True
    state["approval_type"] = "product_spec"
    state["approved"] = False
    state["current_step"] = "llm_product_spec_created"

    return state
