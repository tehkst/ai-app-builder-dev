import json

from app.ai.llm import llm
from app.ai.state import ProjectState
from app.ai.schemas.file_manifest_schema import FileManifest


def fixer_node(state: ProjectState) -> ProjectState:
    review_feedback = state["review_feedback"]
    manifest = state.get("file_manifest", {})

    structured_llm = llm.with_structured_output(
        FileManifest,
        method="function_calling",
    )

    prompt = f"""
You are a senior software engineer and cybersecurity expert.

The reviewer found issues in this generated multi-file app.

Review feedback:
{review_feedback}

Current file manifest:
{json.dumps(manifest, indent=2)}

Fix the app.

STRICT RULES:
- Same schema as FileManifest
- Keep file_path safe and relative
- No hardcoded secrets
- Use environment variables
- No markdown
- No shell commands
- No placeholders like TODO
- You must preserve every file from the current file_manifest.
- Do not delete files.
- Do not reduce the number of files.
- The fixed manifest must contain the exact same file_path list as the input manifest.
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
            "review_feedback": "Fixer attempted to change file list. Human review required.",
            "review_status": "FAIL",
            "current_step": "human_review_required",
        }

    return {
        **state,
        "file_manifest": fixed_manifest.model_dump(),
        "fix_attempts": state.get("fix_attempts", 0) + 1,
        "current_step": "fix_completed",
    }
