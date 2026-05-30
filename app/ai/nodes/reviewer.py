from app.ai.llm import invoke_llm
from app.ai.state import ProjectState


def reviewer_node(state: ProjectState) -> ProjectState:

    manifest_validation = state.get("manifest_validation", {})

    dependency_report = state.get("dependency_report", {})

    contract_report = state.get("contract_report", {})

    files = state.get("file_manifest", {}).get("files", [])

    file_text = "\n\n".join(
        [
            f"FILE: {file.get('file_path')}\n{file.get('content', '')[:3000]}"
            for file in files
        ]
    )

    prompt = f"""
You are a senior enterprise QA and cybersecurity reviewer.

Review the following generated code.

Check for:
- syntax issues
- security issues
- missing imports
- unsafe secrets
- weak authentication
- bad architecture
- non-runnable code
- missing dependencies
- frontend/backend mismatch

Manifest validation:
{manifest_validation}

Dependency report:
{dependency_report}

Contract report:
{contract_report}

Generated files:
{file_text}

Return:
1. Overall status: PASS or FAIL
2. Critical issues
3. Recommended fixes
4. Security concerns
5. Whether this app is safe to write/run locally


Enterprise review rules:
- Fail if any referenced import is missing from the file manifest.
- Fail if frontend calls an API endpoint not generated in backend.
- Fail if authentication lacks JWT create, verify, login, register, and current-user dependency.
- Fail if RBAC is missing.
- Fail if secrets are hardcoded.
- Fail if .env.example is missing.
- Fail if any module is too large and should be split.
- Pass only if the app is structurally runnable.
"""

    response = invoke_llm(prompt)

    review_status = "FAIL"

    if "Overall Status: PASS" in response.content or "PASS" in response.content[:100]:
        review_status = "PASS"

    return {
        **state,
        "review_feedback": response.content,
        "review_status": review_status,
        "current_step": "review_completed",
    }
