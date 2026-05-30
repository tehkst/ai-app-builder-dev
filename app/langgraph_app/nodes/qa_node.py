from app.langgraph_app.state import AppBuilderState


async def qa_node(state: AppBuilderState) -> AppBuilderState:
    generated_files = state.get("generated_files", [])

    issues = []

    if not generated_files:
        issues.append("No generated files found.")

    required_files = ["README.md", "backend/main.py", "frontend/app/page.tsx"]
    generated_paths = [file.get("file_path") for file in generated_files]

    for required_file in required_files:
        if required_file not in generated_paths:
            issues.append(f"Missing required file: {required_file}")

    qa_report = {
        "status": "passed" if not issues else "failed",
        "summary": "Basic QA checks completed.",
        "issues": issues,
        "checks": {
            "files_generated": len(generated_files),
            "required_files_present": len(issues) == 0,
        },
    }

    state["qa_report"] = qa_report
    state["current_step"] = "qa_completed"

    return state
