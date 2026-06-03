from app.ai.llm import invoke_llm
from app.ai.state import ProjectState


def runtime_error_analyzer_node(state: ProjectState) -> ProjectState:
    runtime_report = state.get("runtime_report", {})
    issues = runtime_report.get("issues", [])
    checks = runtime_report.get("checks", [])

    prompt = f"""
You are a senior Python/FastAPI runtime debugging assistant.

Analyze this generated app runtime validation failure and produce a focused repair brief.

Runtime report:
{runtime_report}

Failed checks:
{checks}

Issues:
{issues}

Return a concise repair brief with:
1. Root cause
2. Most likely file or files to fix
3. Exact type of fix needed
4. Whether regeneration is required

Do not invent unrelated production improvements.
Focus only on making the generated app pass runtime validation.
"""

    if runtime_report.get("passed") is True:
        return {
            **state,
            "runtime_error_analysis": {
                "required": False,
                "summary": "Runtime validation passed. No analysis required.",
            },
            "current_step": "runtime_error_analysis_skipped",
        }

    response = invoke_llm(prompt)
    analysis = response.content.strip()

    return {
        **state,
        "runtime_error_analysis": {
            "required": True,
            "summary": analysis,
            "runtime_report": runtime_report,
        },
        "current_step": "runtime_error_analyzed",
    }
