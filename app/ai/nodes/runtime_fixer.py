import json

from app.ai.llm import llm
from app.ai.state import ProjectState
from app.ai.schemas.file_manifest_schema import FileManifest


def runtime_fixer_node(state: ProjectState) -> ProjectState:
    manifest = state.get("file_manifest", {})
    runtime_report = state.get("runtime_report", {})
    runtime_error_analysis = state.get("runtime_error_analysis", {})

    structured_llm = llm.with_structured_output(
        FileManifest,
        method="function_calling",
    )

    prompt = f"""
You are a senior Python/FastAPI runtime repair engineer.

A generated multi-file app failed runtime validation after files were written.

Runtime report:
{json.dumps(runtime_report, indent=2)}

Runtime error analysis:
{json.dumps(runtime_error_analysis, indent=2)}

Current file manifest:
{json.dumps(manifest, indent=2)}

Repair only the issue needed to pass runtime validation.

STRICT RULES:
- Same schema as FileManifest
- Keep file_path safe and relative
- No hardcoded secrets
- Use environment variables
- No markdown
- No shell commands
- No placeholders like TODO
- Preserve every file from the current file_manifest
- Do not delete files
- Do not reduce the number of files
- The fixed manifest must contain the exact same file_path list as the input manifest
- Do not make unrelated production enhancements
- Focus only on fixing runtime validation failures such as SyntaxError, ImportError, ModuleNotFoundError, type errors, or bad startup imports
"""

    fixed_manifest = structured_llm.invoke(prompt)

    original_paths = {
        file.get("file_path")
        for file in manifest.get("files", [])
    }

    fixed_paths = {
        file.file_path
        for file in fixed_manifest.files
    }

    if original_paths != fixed_paths:
        return {
            **state,
            "runtime_error_analysis": {
                **runtime_error_analysis,
                "repair_failed": True,
                "repair_failure_reason": "Runtime fixer attempted to change file list. Human review required.",
            },
            "current_step": "runtime_human_review_required",
        }

    return {
        **state,
        "file_manifest": fixed_manifest.model_dump(),
        "runtime_fix_attempts": state.get("runtime_fix_attempts", 0) + 1,
        "current_step": "runtime_fix_completed",
    }
