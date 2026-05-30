from app.langgraph_app.state import AppBuilderState


DANGEROUS_PATTERNS = [
    "OPENAI_API_KEY=",
    "LANGCHAIN_API_KEY=",
    "password=",
    "secret=",
    "eval(",
    "exec(",
    "subprocess",
    "os.system",
]


async def security_node(state: AppBuilderState) -> AppBuilderState:
    generated_files = state.get("generated_files", [])

    findings = []

    for file in generated_files:
        content = file.get("content", "")
        file_path = file.get("file_path", "")

        for pattern in DANGEROUS_PATTERNS:
            if pattern in content:
                findings.append(
                    {
                        "file_path": file_path,
                        "pattern": pattern,
                        "severity": "high",
                    }
                )

    security_report = {
        "risk_level": "low" if not findings else "high",
        "summary": "Basic generated-code security scan completed.",
        "findings": findings,
    }

    state["security_report"] = security_report
    state["approval_required"] = True
    state["approval_type"] = "generated_app"
    state["approved"] = False
    state["current_step"] = "security_completed"

    return state
