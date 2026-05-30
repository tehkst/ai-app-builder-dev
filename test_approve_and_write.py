import asyncio

from app.langgraph_app.resume_graph import build_resume_graph
from app.services.file_writer_service import safe_write_generated_files


resume_graph = build_resume_graph()

approved_architecture_state = {
    "project_id": "test-project-006",
    "user_id": "toni",
    "organization_id": "schoolber",
    "approval_type": "architecture",
    "approved": True,
    "product_spec": {
        "app_name": "Startup CRM Platform",
        "summary": "A SaaS CRM platform for startups.",
    },
    "architecture_plan": {
        "frontend": {"framework": "Next.js"},
        "backend": {"framework": "FastAPI"},
        "database": {"type": "PostgreSQL"},
    },
}


async def main():
    result = await resume_graph.ainvoke(approved_architecture_state)

    print("Workflow step:")
    print(result["current_step"])

    print("QA report:")
    print(result.get("qa_report"))

    print("Security report:")
    print(result.get("security_report"))

    if (
        result.get("approval_type") == "generated_app"
        and result.get("approved") is False
        and result.get("security_report", {}).get("risk_level") == "low"
    ):
        print("Generated app is ready for final human approval.")

        # Simulate final human approval
        final_human_approval = True

        if final_human_approval:
            written_files = safe_write_generated_files(
                project_id=result["project_id"],
                generated_files=result["generated_files"],
            )

            print("Approved and written files:")
            for file_path in written_files:
                print(file_path)


asyncio.run(main())
