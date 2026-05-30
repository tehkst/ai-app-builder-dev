import asyncio

from app.langgraph_app.resume_graph import build_resume_graph


resume_graph = build_resume_graph()

approved_product_spec_state = {
    "project_id": "test-project-004",
    "user_id": "toni",
    "organization_id": "schoolber",
    "approval_type": "product_spec",
    "approved": True,
    "product_spec": {
        "app_name": "Startup CRM Platform",
        "pages": [
            "Login Page",
            "Dashboard",
            "Customer Management Page",
            "Admin Management Page",
            "Audit Logs Page",
        ],
        "api_modules": [
            "Authentication API",
            "Customer Management API",
            "Analytics API",
            "Admin Management API",
            "Audit Logging API",
        ],
        "database_entities": [
            "Users",
            "Customers",
            "Analytics Data",
            "Admin Settings",
            "Audit Logs",
        ],
    },
}


async def main():
    result = await resume_graph.ainvoke(approved_product_spec_state)

    print(result["current_step"])
    print(result["architecture_plan"])


asyncio.run(main())
