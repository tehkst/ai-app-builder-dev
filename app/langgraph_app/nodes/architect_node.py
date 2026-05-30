from app.langgraph_app.state import AppBuilderState


async def architect_node(state: AppBuilderState) -> AppBuilderState:
    product_spec = state.get("product_spec", {})

    architecture_plan = {
        "architecture_type": "modular_enterprise_saas",
        "frontend": {
            "framework": "Next.js",
            "ui": "Tailwind CSS",
            "pages": product_spec.get("pages", []),
        },
        "backend": {
            "framework": "FastAPI",
            "api_modules": product_spec.get("api_modules", []),
        },
        "database": {
            "type": "PostgreSQL",
            "entities": product_spec.get("database_entities", []),
        },
        "security": {
            "authentication": "JWT / OAuth-ready",
            "authorization": "Role-based access control",
            "audit_logging": True,
            "data_protection": "Encryption-ready",
        },
        "deployment": {
            "containerization": "Docker",
            "environment": "Cloud-ready",
        },
    }

    state["architecture_plan"] = architecture_plan
    state["approval_required"] = True
    state["approval_type"] = "architecture"
    state["approved"] = False
    state["current_step"] = "architecture_plan_created"

    return state
