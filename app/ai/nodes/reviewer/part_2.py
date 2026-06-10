# Split from the legacy module to keep each Python file under 200 lines.
from typing import Dict, List
from app.ai.llm import invoke_node_llm
from app.ai.state import ProjectState

def reviewer_node(state: ProjectState) -> ProjectState:

    manifest_validation = state.get("manifest_validation", {})

    workspace_isolation_report = state.get("workspace_isolation_report", {})

    dependency_report = state.get("dependency_report", {})

    contract_report = state.get("contract_report", {})

    files = state.get("file_manifest", {}).get("files", [])

    file_text = "\n\n".join(
        [
            f"FILE: {file.get('file_path')}\n{file.get('content', '')[:3000]}"
            for file in files
        ]
    )

    security_features = detect_security_features(files)

    blocking_issues = []

    if workspace_isolation_report and not workspace_isolation_report.get("passed", True):
        blocking_issues.append("Workspace isolation guard failed")

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

Platform isolation policy:
- Generated customer apps must never modify the AI SaaS platform code.
- Generated files must stay inside the generated customer app workspace.
- Platform folders such as app/, billing/, dashboard/, auth/, platform/, .github/, and tests/ are not valid generated app targets.

Check for:
- syntax issues
- missing imports
- unsafe hardcoded real secrets
- broken authentication wiring
- missing required backend files
- missing required frontend files
- frontend/backend endpoint mismatch
- failed workspace isolation guard
- failed manifest validation
- failed dependency guard
- failed contract guard

Workspace isolation report:
{workspace_isolation_report}

Manifest validation:
{manifest_validation}

Dependency report:
{dependency_report}

Contract report:
{contract_report}

Detected security features:
{security_features}

Generated files:
{file_text}

Return:
1. Overall Status: PASS or FAIL
2. Blocking issues
3. Non-blocking warnings
4. Recommended fixes
5. Whether this app is safe to write/run locally

Enterprise review rules:
- PASS if workspace isolation passed, manifest validation passed, dependency guard passed, contract guard passed, and no obvious syntax/import blocker is found.
- FAIL if workspace isolation guard failed.
- FAIL if any referenced import is missing from the file manifest.
- FAIL if frontend calls an API endpoint that clearly does not exist in backend.
- FAIL if authentication lacks JWT create, decode, login, register, and current-user dependency.
- FAIL if secrets are hardcoded as real values in source files.
- Do not fail for placeholder secrets in .env.example.
- Do not fail for missing production features such as account lockout, audit logs, or advanced RBAC.
- If detected security features show membership_rbac_present=True, do not warn that RBAC is fake or missing.
- If detected security features show blind_rbac_present=True, warn that RBAC is only a placeholder.
- If detected security features show rate_limit_present=True, do not warn that rate limiting is missing.
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

    response = invoke_node_llm(
        state,
        "reviewer",
        prompt,
        metadata={
            "workspace_isolation_passed": workspace_isolation_report.get("passed"),
            "manifest_validation_passed": manifest_validation.get("passed"),
            "dependency_guard_passed": dependency_report.get("passed"),
            "contract_guard_passed": contract_report.get("passed"),
            "rate_limit_present": security_features.get("rate_limit_present"),
            "membership_rbac_present": security_features.get("membership_rbac_present"),
            "blind_rbac_present": security_features.get("blind_rbac_present"),
        },
    )

    content = response.content.strip()
    normalized = normalize_review_feedback(content)

    review_status = "FAIL"

    if "overall status: pass" in normalized:
        review_status = "PASS"

    return {
        **state,
        "review_feedback": content,
        "review_status": review_status,
        "current_step": "review_completed",
    }
