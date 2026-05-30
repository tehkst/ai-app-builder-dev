import asyncio

from app.langgraph_app.resume_graph import build_resume_graph


resume_graph = build_resume_graph()

approved_architecture_state = {
    "project_id": "test-project-005",
    "user_id": "toni",
    "organization_id": "schoolber",
    "approval_type": "architecture",
    "approved": True,
    "product_spec": {
        "app_name": "Startup CRM Platform",
        "summary": "A SaaS CRM platform for startups.",
    },
    "architecture_plan": {
        "frontend": {
            "framework": "Next.js",
        },
        "backend": {
            "framework": "FastAPI",
        },
        "database": {
            "type": "PostgreSQL",
        },
    },
}


async def main():
    result = await resume_graph.ainvoke(approved_architecture_state)

    print(result["current_step"])

    for file in result["generated_files"]:
        print("------")
        print(file["file_path"])
        print(file["file_type"])
        print(file["content"][:300])


asyncio.run(main())
