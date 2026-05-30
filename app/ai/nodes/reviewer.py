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

    blocking_issues = []

    if manifest_validation and not manifest_validation.get("passed", True):
        blocking_issues.append("Manifest validation failed")

    if dependency_report and not dependency_report.get("passed", True):
        blocking_issues.append("Dependency guard failed")

    if contract_report and not contract_report.get("passed", True):
        blocking_issues.append("Contract guard failed")

    prompt = f"""
You are a senior enterprise QA and cybersecurity reviewer.

Review the following generated code.

This is an MVP-safe generated app, not a final production banking system.

Important review policy:
- .env.example files are allowed to contain placeholders.
- Do not fail because JWT_SECRET_KEY is a placeholder in .env.example.
- Missing rate limiting is a warning, not a blocker.
- Basic RBAC with require_role is acceptable for MVP if the dependency exists.
- Do not fail because RBAC is not fully production-grade.
- Do not fail because account lockout is missing.
- Do not fail because secrets are expected to be supplied by environment variables.
- Fail only for structural blockers that would make the app unsafe to write or clearly non-runnable.

Check for:
- syntax issues
- missing imports
- unsafe hardcoded real secrets
- broken authentication wiring
- missing required backend files
- missing required frontend files
- frontend/backend endpoint mismatch
- failed manifest validation
- failed dependency guard
- failed contract guard

Manifest validation:
{manifest_validation}

Dependency report:
{dependency_report}

Contract report:
{contract_report}

Generated files:
{file_text}

Return:
1. Overall Status: PASS or FAIL
2. Blocking issues
3. Non-blocking warnings
4. Recommended fixes
5. Whether this app is safe to write/run locally

Enterprise review rules:
- PASS if manifest validation passed, dependency guard passed, contract guard passed, and no obvious syntax/import blocker is found.
- FAIL if any referenced import is missing from the file manifest.
- FAIL if frontend calls an API endpoint that clearly does not exist in backend.
- FAIL if authentication lacks JWT create, decode, login, register, and current-user dependency.
- FAIL if secrets are hardcoded as real values in source files.
- Do not fail for placeholder secrets in .env.example.
- Do not fail for missing production features such as rate limiting, account lockout, audit logs, or advanced RBAC.
"""

    if blocking_issues:
        review_status = "FAIL"
        response_content = (
            "Overall Status: FAIL\n\n"
            "Blocking issues detected before LLM review:\n"
            + "\n".join(f"- {issue}" for issue in blocking_issues)
        )

        return {
            **state,
            "review_feedback": response_content,
            "review_status": review_status,
            "current_step": "review_completed",
        }

    response = invoke_llm(prompt)

    review_status = "FAIL"
    content = response.content.strip()

    normalized = content.lower()

    if (
        "overall status: pass" in normalized
        or "overall status:** pass" in normalized
        or "overall status: **pass**" in normalized
    ):
        review_status = "PASS"

    return {
        **state,
        "review_feedback": content,
        "review_status": review_status,
        "current_step": "review_completed",
    }
