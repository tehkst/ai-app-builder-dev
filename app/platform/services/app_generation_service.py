from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from app.platform.runtime.service import invoke_ai

MAX_REPAIR_ATTEMPTS = 1
PLACEHOLDER_PATTERN = re.compile(r"\b(?:TODO|TBD|PSEUDOCODE|IMPLEMENT HERE|FIXME|\.\.\.)\b", re.IGNORECASE)
PATH_PATTERN = re.compile(r"[A-Za-z0-9_.@+/-]+")

REQUIRED_SCHEMA = {
    "app_name": "short app name",
    "summary": "one paragraph description of what the app does",
    "files": [
        {
            "path": "relative file path, e.g. backend/app/routes.py",
            "language": "python | typescript | javascript | json | markdown | css | html",
            "purpose": "why this file exists",
            "content": "complete file content, no placeholders",
        }
    ],
    "assumptions": ["assumption strings"],
    "risks": ["risk strings"],
}

SYSTEM_PROMPT = (
    "You are a senior full-stack engineer generating a complete, working application "
    "for a customer request. Return JSON only, matching the required schema exactly. "
    "Every file's content must be complete and runnable: no TODOs, no placeholders, no "
    "pseudocode, no '...'. Tailor the data model, API routes, and UI specifically to the "
    "customer's stated goal and acceptance criteria — never default to an unrelated "
    "example domain. Use FastAPI (Python) for the backend and React (JSX) for the frontend "
    "unless the request says otherwise. Keep the file set minimal but complete: models, "
    "schemas, service layer, API routes, one frontend view, and a README."
)

REVIEW_SYSTEM_PROMPT = (
    "You are a senior staff engineer performing an independent code review of another "
    "engineer's generated application. You did not write this code - review it with "
    "fresh eyes for real, concrete defects: bugs, security issues, logic errors, and "
    "places where the implementation does not actually satisfy the stated scope of work "
    "or acceptance criteria. Do not comment on style or preference. Return JSON only: "
    '{"approved": true|false, "findings": ["specific, concrete issue strings"]}. '
    "approved must be false if there is any finding a real user-facing app cannot ship "
    "with. An empty findings list with approved true means you found nothing worth "
    "blocking on."
)


def review_app_build_files(
    *,
    app_request: str,
    scope_of_work_markdown: str = "",
    acceptance_criteria: Optional[List[str]] = None,
    out_of_scope: Optional[List[str]] = None,
    generated_files: List[Dict[str, Any]],
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Independent cross-model review of already-generated application files.

    Returns None if the reviewer itself was unavailable (provider error, timeout,
    unparsable output) so the caller can distinguish "no reviewer available" - which
    must not block a build - from "reviewer found problems" - which should.
    """

    prompt_context = _prompt_context(
        app_request=app_request,
        scope_of_work_markdown=scope_of_work_markdown,
        acceptance_criteria=acceptance_criteria or [],
        out_of_scope=out_of_scope or [],
    )
    review_prompt = {
        **prompt_context,
        "task": "Review the following generated application files for concrete defects.",
        "generated_files": [
            {"path": item.get("path"), "language": item.get("language"), "content": item.get("content")}
            for item in generated_files
        ],
    }
    ai_result = invoke_ai(
        {
            "provider": provider,
            "model": model,
            "system": REVIEW_SYSTEM_PROMPT,
            "prompt": json.dumps(review_prompt, sort_keys=True),
        }
    )
    if ai_result.get("status") != "completed":
        return None

    parsed, parse_error = _parse_model_output(str(ai_result.get("output_text") or ""))
    if parse_error:
        return None

    findings = _string_list(parsed.get("findings"))
    approved = bool(parsed.get("approved")) and not findings
    return {
        "approved": approved,
        "findings": findings,
        "provider": ai_result.get("provider"),
        "model": ai_result.get("model"),
    }


def repair_app_build_files(
    *,
    app_request: str,
    scope_of_work_markdown: str = "",
    acceptance_criteria: Optional[List[str]] = None,
    out_of_scope: Optional[List[str]] = None,
    previous_files: List[Dict[str, Any]],
    review_findings: List[str],
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Apply one bounded repair pass against independent review findings.

    Seeded with the previous generation's own files (so the model fixes them in
    place rather than regenerating from scratch) plus the reviewer's concrete
    findings. Returns the same success/blocked shape as generate_app_build_files.
    """

    prompt_context = _prompt_context(
        app_request=app_request,
        scope_of_work_markdown=scope_of_work_markdown,
        acceptance_criteria=acceptance_criteria or [],
        out_of_scope=out_of_scope or [],
    )
    repair_prompt = {
        **prompt_context,
        "task": "Repair the generated application to resolve every independent code review finding.",
        "previous_files": [
            {"path": item.get("path"), "language": item.get("language"), "content": item.get("content")}
            for item in previous_files
        ],
        "previous_attempt_failure_reason": "Independent code review found blocking issues.",
        "failed_checks": [{"name": "independent_review", "reason": finding} for finding in review_findings],
        "repair_constraints": [
            "Resolve every listed review finding.",
            "Return the complete corrected file set, not a partial patch.",
            "Do not remove functionality unrelated to the findings.",
            "This is the only automatic repair attempt for this review.",
        ],
    }
    ai_result = _invoke_generation(repair_prompt, provider=provider, model=model)
    if ai_result.get("status") != "completed":
        return _blocked(
            reason=f"AI repair generation was unavailable: {ai_result.get('status')}.",
            ai_result=ai_result,
            repair_attempt_count=1,
        )

    generated, parse_error = _parse_model_output(str(ai_result.get("output_text") or ""))
    if parse_error:
        return _blocked(reason=parse_error, ai_result=ai_result, repair_attempt_count=1)

    files, checks = _validate_generated_files(generated)
    if not all(check["passed"] for check in checks):
        failed_checks = [check for check in checks if not check["passed"]]
        return _blocked(
            reason="Repaired application did not pass structural validation.",
            ai_result=ai_result,
            repair_attempt_count=1,
            failed_checks=failed_checks,
        )

    return {
        "success": True,
        "status": "repaired",
        "app_name": str(generated.get("app_name") or "").strip() or "Generated App",
        "summary": str(generated.get("summary") or "").strip(),
        "files": files,
        "assumptions": _string_list(generated.get("assumptions")),
        "risks": _string_list(generated.get("risks")),
        "generation": {
            "provider": ai_result.get("provider"),
            "model": ai_result.get("model"),
            "repair_attempt_count": 1,
        },
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "filesystem_write_performed": False,
        "generated_code_execution_performed": False,
        "external_deployment_performed": False,
        "materialization_performed": False,
    }


def generate_app_build_files(
    *,
    app_request: str,
    scope_of_work_markdown: str = "",
    acceptance_criteria: Optional[List[str]] = None,
    out_of_scope: Optional[List[str]] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate request-specific application files using a real LLM call.

    Unlike a template-based generator, this grounds the model in the approved
    scope of work (SOW) and validates its output structurally before returning
    it, with one bounded automatic repair attempt if validation fails.
    """

    prompt_context = _prompt_context(
        app_request=app_request,
        scope_of_work_markdown=scope_of_work_markdown,
        acceptance_criteria=acceptance_criteria or [],
        out_of_scope=out_of_scope or [],
    )

    ai_result = _invoke_generation(prompt_context, provider=provider, model=model)
    if ai_result.get("status") != "completed":
        return _blocked(
            reason=f"AI generation was unavailable: {ai_result.get('status')}.",
            ai_result=ai_result,
        )

    output_text = str(ai_result.get("output_text") or "")
    generated, parse_error = _parse_model_output(output_text)
    repair_attempt_count = 0

    if parse_error:
        generated, parse_error, ai_result = _attempt_repair(
            prompt_context,
            reason=parse_error,
            failed_checks=[{"name": "json_parse", "reason": parse_error}],
            provider=provider,
            model=model,
        )
        repair_attempt_count = 1
        if parse_error:
            return _blocked(reason=parse_error, ai_result=ai_result, repair_attempt_count=repair_attempt_count)

    files, checks = _validate_generated_files(generated)
    if not all(check["passed"] for check in checks):
        failed_checks = [check for check in checks if not check["passed"]]
        generated_repaired, parse_error, ai_result = _attempt_repair(
            prompt_context,
            reason="Structural validation failed.",
            failed_checks=failed_checks,
            provider=provider,
            model=model,
        )
        repair_attempt_count = 1
        if parse_error:
            return _blocked(reason=parse_error, ai_result=ai_result, repair_attempt_count=repair_attempt_count)
        files, checks = _validate_generated_files(generated_repaired)
        generated = generated_repaired
        if not all(check["passed"] for check in checks):
            failed_checks = [check for check in checks if not check["passed"]]
            return _blocked(
                reason="Generated application did not pass structural validation after one repair attempt.",
                ai_result=ai_result,
                repair_attempt_count=repair_attempt_count,
                failed_checks=failed_checks,
            )

    return {
        "success": True,
        "status": "generated",
        "app_name": str(generated.get("app_name") or "").strip() or "Generated App",
        "summary": str(generated.get("summary") or "").strip(),
        "files": files,
        "assumptions": _string_list(generated.get("assumptions")),
        "risks": _string_list(generated.get("risks")),
        "generation": {
            "provider": ai_result.get("provider"),
            "model": ai_result.get("model"),
            "repair_attempt_count": repair_attempt_count,
        },
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "filesystem_write_performed": False,
        "generated_code_execution_performed": False,
        "external_deployment_performed": False,
        "materialization_performed": False,
    }


def _prompt_context(
    *,
    app_request: str,
    scope_of_work_markdown: str,
    acceptance_criteria: List[str],
    out_of_scope: List[str],
) -> Dict[str, Any]:
    return {
        "task": "Generate the smallest complete application that satisfies the approved scope of work.",
        "required_schema": REQUIRED_SCHEMA,
        "customer_request": app_request,
        "approved_scope_of_work": scope_of_work_markdown,
        "acceptance_criteria": acceptance_criteria,
        "out_of_scope": out_of_scope,
        "constraints": [
            "Only produce files relevant to this request.",
            "Return complete file contents, not diffs or partial snippets.",
            "Do not include TODOs, pseudocode, or placeholder content.",
            "Do not perform database migrations, external deployment, or package installation.",
        ],
    }


def _invoke_generation(
    prompt_context: Dict[str, Any],
    *,
    provider: Optional[str],
    model: Optional[str],
) -> Dict[str, Any]:
    return invoke_ai(
        {
            "provider": provider,
            "model": model,
            "system": SYSTEM_PROMPT,
            "prompt": json.dumps(prompt_context, sort_keys=True),
        }
    )


def _attempt_repair(
    prompt_context: Dict[str, Any],
    *,
    reason: str,
    failed_checks: List[Dict[str, Any]],
    provider: Optional[str],
    model: Optional[str],
) -> Tuple[Dict[str, Any], Optional[str], Dict[str, Any]]:
    repair_prompt = {
        **prompt_context,
        "task": "Repair the invalid generated application and return the complete corrected schema.",
        "previous_attempt_failure_reason": reason,
        "failed_checks": failed_checks,
        "repair_constraints": [
            "Correct every failed check.",
            "Return the complete corrected file set, not a partial patch.",
            "This is the only automatic repair attempt.",
        ],
    }
    ai_result = _invoke_generation(repair_prompt, provider=provider, model=model)
    if ai_result.get("status") != "completed":
        return {}, f"AI repair generation was unavailable: {ai_result.get('status')}.", ai_result

    output_text = str(ai_result.get("output_text") or "")
    generated, parse_error = _parse_model_output(output_text)
    return generated, parse_error, ai_result


def _parse_model_output(text: str) -> Tuple[Dict[str, Any], Optional[str]]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        value = json.loads(cleaned)
    except (TypeError, json.JSONDecodeError):
        return {}, "Generated output was not valid structured JSON."
    if not isinstance(value, dict):
        return {}, "Generated output must be a JSON object."
    return value, None


def _validate_generated_files(generated: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    files_value = generated.get("files")
    raw_files = files_value if isinstance(files_value, list) else []
    files: List[Dict[str, Any]] = []
    checks: List[Dict[str, Any]] = []
    seen_paths: set = set()

    checks.append(_check("files_schema", isinstance(files_value, list), "The files field must be a list."))
    checks.append(_check("files_present", bool(raw_files), "At least one generated file is required."))

    for index, item in enumerate(raw_files):
        if not isinstance(item, dict):
            checks.append(_check(f"file_{index}_schema", False, "File entry must be an object.", index=index))
            continue

        path = str(item.get("path") or "").strip()
        content = item.get("content")
        language = str(item.get("language") or "").strip()
        purpose = str(item.get("purpose") or "").strip()

        valid_path = _safe_relative_path(path)
        checks.append(_check(f"file_{index}_path", valid_path, "File path is missing or unsafe.", path=path, index=index))

        unique = bool(path) and path not in seen_paths
        checks.append(_check(f"file_{index}_unique", unique, "File path is duplicated.", path=path, index=index))
        seen_paths.add(path)

        has_content = isinstance(content, str) and bool(content.strip())
        checks.append(_check(f"file_{index}_content_present", has_content, "File content is empty.", path=path, index=index))

        no_placeholder = has_content and not PLACEHOLDER_PATTERN.search(content)
        checks.append(_check(f"file_{index}_no_placeholder", no_placeholder, "File content contains a placeholder marker.", path=path, index=index))

        syntax_ok = _python_syntax_ok(path, content if isinstance(content, str) else "")
        checks.append(_check(f"file_{index}_python_syntax", syntax_ok, "Generated Python content does not parse.", path=path, index=index))

        if valid_path and unique and has_content and no_placeholder and syntax_ok:
            files.append(
                {
                    "path": path,
                    "language": language or _infer_language(path),
                    "purpose": purpose,
                    "content": content,
                    "content_preview": content[:240],
                    "write_status": "generated",
                }
            )

    return files, checks


def _safe_relative_path(path: str) -> bool:
    if not path or path.startswith("/") or "\\" in path or ".." in path.split("/"):
        return False
    return bool(PATH_PATTERN.fullmatch(path))


def _python_syntax_ok(path: str, content: str) -> bool:
    if not path.endswith(".py") or not content:
        return True
    try:
        ast.parse(content)
        return True
    except SyntaxError:
        return False


def _infer_language(path: str) -> str:
    if path.endswith(".py"):
        return "python"
    if path.endswith((".ts", ".tsx")):
        return "typescript"
    if path.endswith((".js", ".jsx")):
        return "javascript"
    if path.endswith(".json"):
        return "json"
    if path.endswith(".css"):
        return "css"
    if path.endswith(".html"):
        return "html"
    if path.endswith(".md"):
        return "markdown"
    return "text"


def _check(name: str, passed: bool, reason: str, *, path: Optional[str] = None, index: Optional[int] = None) -> Dict[str, Any]:
    return {"name": name, "passed": bool(passed), "reason": reason, "path": path, "index": index}


def _string_list(value: Any) -> List[str]:
    return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []


def _blocked(
    *,
    reason: str,
    ai_result: Dict[str, Any],
    repair_attempt_count: int = 0,
    failed_checks: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "success": False,
        "status": "blocked",
        "app_name": None,
        "summary": None,
        "files": [],
        "assumptions": [],
        "risks": [],
        "blocked_reason": reason,
        "failed_checks": failed_checks or [],
        "generation": {
            "provider": ai_result.get("provider"),
            "model": ai_result.get("model"),
            "repair_attempt_count": repair_attempt_count,
            "provider_status": ai_result.get("status"),
        },
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "filesystem_write_performed": False,
        "generated_code_execution_performed": False,
        "external_deployment_performed": False,
        "materialization_performed": False,
    }
