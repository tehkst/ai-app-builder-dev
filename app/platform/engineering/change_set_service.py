from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.platform.execution.service import get_execution_mission_evidence, record_execution_mission_evidence
from app.platform.runtime.service import invoke_ai


REPO_ROOT = Path(__file__).resolve().parents[3]
MAX_FILES = 8
MAX_FILE_CHARS = 60_000
MAX_CONTEXT_CHARS = 180_000
SUPPORTED_OPERATIONS = {"create", "update"}
PLACEHOLDER_PATTERN = re.compile(r"\b(?:TODO|TBD|PSEUDOCODE|IMPLEMENT HERE|MODIFY THIS SECTION)\b", re.IGNORECASE)


def generate_executable_change_set(payload: dict[str, Any]) -> dict[str, Any]:
    mission_id = str(payload.get("mission_id") or "").strip()
    supplied_evidence = isinstance(payload.get("mission_evidence"), dict)
    mission = payload.get("mission_evidence") if supplied_evidence else get_execution_mission_evidence(mission_id) or {}
    evidence_error = _evidence_error(mission_id, mission)
    if evidence_error:
        return _blocked(mission_id or None, evidence_error)
    plan_result = mission["planning_result"]
    plan = plan_result["plan"]
    handoff = mission["engineering_handoff"]
    target_paths = _target_paths(payload, plan)
    context, context_error = _repository_context(target_paths)
    if context_error:
        return _blocked(mission_id, context_error, plan, handoff)
    context_fingerprint = _context_fingerprint(context)
    existing = mission.get("executable_change_set") if isinstance(mission.get("executable_change_set"), dict) else {}
    if _reusable(existing, mission_id, plan.get("plan_id"), handoff.get("breakdown_id"), context_fingerprint):
        return {**existing, "reused": True}
    prompt_context = _generation_prompt_context(mission_id, mission, plan, handoff, context)
    ai_result = _invoke_generation(payload, prompt_context)
    if ai_result.get("status") != "completed":
        return _blocked(mission_id, "AI implementation generation was unavailable.", plan, handoff, ai_result)
    output_text = str(ai_result.get("output_text") or "")
    generated, parse_error = _parse_model_output(output_text)
    if parse_error:
        diagnostics = [_parse_diagnostic(output_text, parse_error, 1)]
        result = _blocked(mission_id, parse_error, plan, handoff, diagnostics=diagnostics)
        _record_change_set(mission_id, result, supplied_evidence)
        return result
    files, checks = _validate_generated_files(generated, context, mission_id)
    validation = {"status": "passed" if all(item["passed"] for item in checks) else "failed", "checks": checks, "commands": _validation_commands(files, handoff)}
    if validation["status"] != "passed":
        first_diagnostic = _attempt_diagnostic(generated, checks, output_text, 1)
        repair_result = _invoke_generation(
            payload,
            {
                **prompt_context,
                "task": "Repair the invalid executable change set and return the complete corrected schema.",
                "original_candidate": generated,
                "failed_checks": first_diagnostic["failed_checks"],
                "repair_constraints": ["Correct every failed check.", "Return every complete approved file change, not a partial patch.", "This is the only automatic repair attempt."],
            },
        )
        if repair_result.get("status") != "completed":
            result = _blocked(mission_id, "Change-set repair generation was unavailable.", plan, handoff, diagnostics=[first_diagnostic], repair_attempt_count=1)
            _record_change_set(mission_id, result, supplied_evidence)
            return result
        repaired_text = str(repair_result.get("output_text") or "")
        repaired, repair_parse_error = _parse_model_output(repaired_text)
        if repair_parse_error:
            diagnostics = [first_diagnostic, _parse_diagnostic(repaired_text, repair_parse_error, 2)]
            result = _blocked(mission_id, "The change set could not pass structural validation after one repair attempt.", plan, handoff, diagnostics=diagnostics, repair_attempt_count=1)
            _record_change_set(mission_id, result, supplied_evidence)
            return result
        files, checks = _validate_generated_files(repaired, context, mission_id)
        validation = {"status": "passed" if all(item["passed"] for item in checks) else "failed", "checks": checks, "commands": _validation_commands(files, handoff)}
        repair_diagnostic = _attempt_diagnostic(repaired, checks, repaired_text, 2)
        if validation["status"] != "passed":
            result = _blocked(mission_id, "The change set could not pass structural validation after one repair attempt.", plan, handoff, diagnostics=[first_diagnostic, repair_diagnostic], repair_attempt_count=1)
            _record_change_set(mission_id, result, supplied_evidence)
            return result
        generated = repaired
        diagnostics = [first_diagnostic, repair_diagnostic]
        repair_attempt_count = 1
        final_ai_result = repair_result
    else:
        diagnostics = [_attempt_diagnostic(generated, checks, output_text, 1)]
        repair_attempt_count = 0
        final_ai_result = ai_result
    result = {
        "mission_id": mission_id,
        "change_set_status": "change_set_ready",
        "source_plan_id": plan.get("plan_id"),
        "engineering_breakdown_id": handoff.get("breakdown_id"),
        "files": files,
        "validation": validation,
        "assumptions": _string_list(generated.get("assumptions")),
        "risks": _string_list(generated.get("risks")),
        "blocked_reason": None,
        "repository_context": [{"path": item["path"], "exists": item["exists"], "operation": item["operation"], "target": item["target"]} for item in context],
        "repository_context_fingerprint": context_fingerprint,
        "generation": {"provider": final_ai_result.get("provider"), "model": final_ai_result.get("model"), "raw_output_exposed": False, "repair_attempt_count": repair_attempt_count, "attempts": diagnostics},
        "reused": False,
        "governance": {"repository_mutation": False, "branch_creation": False, "commit": False, "push": False, "pull_request": False, "merge": False, "deployment": False},
        "next_required_action": "Authorize engineering execution.",
    }
    _record_change_set(mission_id, result, supplied_evidence)
    return result


def _record_change_set(mission_id: str, result: dict[str, Any], supplied_evidence: bool) -> None:
    if not supplied_evidence:
        record_execution_mission_evidence(mission_id, "executable_change_set", result)


def _generation_prompt_context(mission_id: str, mission: dict[str, Any], plan: dict[str, Any], handoff: dict[str, Any], context: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "task": "Produce the smallest complete executable change set for the approved mission.",
        "required_schema": {"mission_id": mission_id, "files": [{"path": "approved target", "operation": "create or update", "content": "complete file content", "rationale": "why required", "source_evidence": ["inspected paths"], "confidence": "high, medium, or low"}], "assumptions": [], "risks": []},
        "mission_id": mission_id,
        "founder_request": mission.get("founder_request"),
        "approved_plan": plan,
        "engineering_breakdown": handoff,
        "repository_context": context,
        "allowed_targets": [{"path": item["path"], "expected_operation": item["operation"]} for item in context if item["target"]],
        "constraints": ["Only use approved target paths.", "Updates must contain complete replacement content.", "Do not include TODOs, pseudocode, vague instructions, branches, commits, PRs, or deployment actions."],
    }


def _invoke_generation(payload: dict[str, Any], prompt: dict[str, Any]) -> dict[str, Any]:
    return invoke_ai({
        "provider": payload.get("provider"),
        "model": payload.get("model"),
        "system": "You are a senior engineer producing executable repository changes. Return JSON only. Use complete file contents, preserve local conventions, and never return placeholders or prose outside the schema.",
        "prompt": json.dumps(prompt, sort_keys=True),
    })


def _evidence_error(mission_id: str, mission: dict[str, Any]) -> str | None:
    if not re.fullmatch(r"MISSION-[A-Za-z0-9][A-Za-z0-9-]*", mission_id):
        return "Canonical mission identity is unresolved or invalid."
    if mission.get("mission_id") != mission_id:
        return "Canonical mission identity conflicts with mission evidence."
    plan_result = mission.get("planning_result") if isinstance(mission.get("planning_result"), dict) else {}
    plan = plan_result.get("plan") if isinstance(plan_result.get("plan"), dict) else {}
    if plan.get("mission_id") != mission_id or not plan.get("plan_id"):
        return "Approved mission-specific plan is missing or contradictory."
    handoff = mission.get("engineering_handoff") if isinstance(mission.get("engineering_handoff"), dict) else {}
    if handoff.get("mission_id") != mission_id or not handoff.get("breakdown_id"):
        return "Mission-specific engineering breakdown is missing or contradictory."
    return None


def _target_paths(payload: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    raw = payload.get("target_files") if isinstance(payload.get("target_files"), list) else plan.get("affected_files") or []
    paths = [str(item.get("path") if isinstance(item, dict) else item).strip() for item in raw if (item.get("path") if isinstance(item, dict) else item)]
    return list(dict.fromkeys(path for path in paths if path))[: MAX_FILES + 1]


def _repository_context(paths: list[str]) -> tuple[list[dict[str, Any]], str | None]:
    if not paths:
        return [], "Approved plan does not identify implementation files."
    if len(paths) > MAX_FILES:
        return [], f"Approved implementation scope exceeds the {MAX_FILES}-file generation boundary."
    context: list[dict[str, Any]] = []
    total = 0
    for path in paths:
        resolved = _safe_path(path)
        if resolved is None:
            return [], f"Invalid repository path: {path}"
        exists = resolved.is_file()
        try:
            content = resolved.read_text(encoding="utf-8") if exists else ""
        except (OSError, UnicodeError):
            return [], f"Required implementation file could not be inspected as text: {path}"
        if len(content) > MAX_FILE_CHARS or total + len(content) > MAX_CONTEXT_CHARS:
            return [], f"Required repository context is too large to inspect safely: {path}"
        total += len(content)
        context.append({"path": path, "exists": exists, "operation": "update" if exists else "create", "content": content, "target": True})
    neighbor_paths: list[Path] = []
    for item in list(context):
        parent = (REPO_ROOT / item["path"]).parent
        initializer = parent / "__init__.py"
        if initializer.is_file():
            neighbor_paths.append(initializer)
        neighbor_paths.extend(sorted(parent.glob("*.py"))[:2])
    existing_paths = {item["path"] for item in context}
    for neighbor in neighbor_paths:
        relative = neighbor.relative_to(REPO_ROOT).as_posix()
        if relative in existing_paths:
            continue
        content = neighbor.read_text(encoding="utf-8")
        if len(content) > MAX_FILE_CHARS or total + len(content) > MAX_CONTEXT_CHARS:
            continue
        total += len(content)
        existing_paths.add(relative)
        context.append({"path": relative, "exists": True, "operation": "reference", "content": content, "target": False})
    return context, None


def _parse_model_output(text: str) -> tuple[dict[str, Any], str | None]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        value = json.loads(cleaned)
    except (TypeError, json.JSONDecodeError):
        return {}, "Generated change set was not valid structured JSON."
    if not isinstance(value, dict):
        return {}, "Generated change set must be a JSON object."
    return value, None


def _validate_generated_files(generated: dict[str, Any], context: list[dict[str, Any]], mission_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    files_value = generated.get("files")
    raw_files = files_value if isinstance(files_value, list) else []
    allowed = {item["path"]: item for item in context if item["target"]}
    inspected = {item["path"] for item in context}
    files: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    seen: set[str] = set()
    checks.append(_check("mission_identity", generated.get("mission_id") == mission_id, "Generated mission ID does not match approved evidence."))
    checks.append(_check("files_schema", isinstance(files_value, list), "The files field must be a list."))
    checks.append(_check("files_present", bool(raw_files), "At least one executable file change is required."))
    for index, item in enumerate(raw_files):
        if not isinstance(item, dict):
            checks.append(_check(f"file_{index}_schema", False, "File change must be an object.", candidate_index=index))
            continue
        path = str(item.get("path") or "").strip()
        operation = str(item.get("operation") or "").strip().lower()
        content = item.get("content")
        source_evidence = _string_list(item.get("source_evidence"))
        valid_path = path in allowed and _safe_path(path) is not None
        checks.append(_check(f"file_{index}_path", valid_path, "File path is not an approved repository target.", path=path, operation=operation, candidate_index=index))
        checks.append(_check(f"file_{index}_unique", bool(path and path not in seen), "File target is duplicated in the candidate.", path=path, operation=operation, candidate_index=index))
        seen.add(path)
        expected = allowed.get(path, {}).get("operation")
        operation_ok = operation in SUPPORTED_OPERATIONS and operation == expected
        checks.append(_check(f"file_{index}_operation", operation_ok, f"Operation must be {expected or 'create or update'} for the inspected target.", path=path, operation=operation, candidate_index=index))
        complete = isinstance(content, str) and bool(content.strip()) and not PLACEHOLDER_PATTERN.search(content)
        checks.append(_check(f"file_{index}_content", complete, "Content is empty, incomplete, or contains an unsupported placeholder.", path=path, operation=operation, candidate_index=index))
        changed = not (operation == "update" and path in allowed and isinstance(content, str) and content == allowed[path]["content"])
        checks.append(_check(f"file_{index}_changed", changed, "Update content is unchanged from the inspected repository file.", path=path, operation=operation, candidate_index=index))
        checks.append(_check(f"file_{index}_evidence", bool(source_evidence) and set(source_evidence).issubset(inspected), "Source evidence is missing or references a file that was not inspected.", path=path, operation=operation, candidate_index=index))
        rationale = str(item.get("rationale") or "").strip()
        checks.append(_check(f"file_{index}_rationale", len(rationale) >= 12 and rationale.lower() not in {"change it.", "update file.", "required change."}, "Rationale is missing, too short, or not mission-specific.", path=path, operation=operation, candidate_index=index))
        checks.append(_check(f"file_{index}_confidence", str(item.get("confidence") or "").strip().lower() in {"high", "medium", "low"}, "Confidence must be high, medium, or low.", path=path, operation=operation, candidate_index=index))
        syntax_ok, imports_ok = _python_validation(path, content if isinstance(content, str) else "")
        checks.append(_check(f"file_{index}_python_syntax", syntax_ok, "Generated Python content does not parse.", path=path, operation=operation, candidate_index=index))
        checks.append(_check(f"file_{index}_local_imports", imports_ok, "Generated Python content references an implausible local module.", path=path, operation=operation, candidate_index=index))
        files.append({"path": path, "operation": operation, "content": content, "rationale": str(item.get("rationale") or "").strip(), "source_evidence": source_evidence, "confidence": str(item.get("confidence") or "low").strip().lower()})
    return files, checks


def _python_validation(path: str, content: str) -> tuple[bool, bool]:
    if not path.endswith(".py"):
        return True, True
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return False, True
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
            module = REPO_ROOT / (node.module.replace(".", "/") + ".py")
            package = REPO_ROOT / node.module.replace(".", "/") / "__init__.py"
            if not module.exists() and not package.exists() and node.module != _module_from_path(path):
                return True, False
    return True, True


def _validation_commands(files: list[dict[str, Any]], handoff: dict[str, Any]) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    python_paths = [item["path"] for item in files if item["path"].endswith(".py")]
    if python_paths:
        commands.append({"command": "python3 -m compileall " + " ".join(python_paths), "purpose": "Compile changed Python modules.", "required": True, "expected_success_condition": "Command exits with status 0."})
    for item in files:
        if item["path"].endswith(".js"):
            commands.append({"command": f"node --check {item['path']}", "purpose": "Validate changed JavaScript syntax.", "required": True, "expected_success_condition": "Command exits with status 0."})
    for value in _string_list(handoff.get("validation_plan")):
        if re.fullmatch(r"(?:python3?|node|bash) [A-Za-z0-9_./:= -]+", value) and value not in {item["command"] for item in commands}:
            commands.append({"command": value, "purpose": "Run the approved mission validation gate.", "required": True, "expected_success_condition": "Command exits with status 0."})
    return commands


def _safe_path(path: str) -> Path | None:
    if not path or path.startswith("/") or "\\" in path or not re.fullmatch(r"[A-Za-z0-9_.@+/-]+", path):
        return None
    candidate = Path(path)
    if any(part in {"", ".", ".."} for part in candidate.parts) or candidate.parts[0] == ".git":
        return None
    resolved = (REPO_ROOT / candidate).resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        return None
    return resolved


def _module_from_path(path: str) -> str:
    return path[:-3].replace("/", ".") if path.endswith(".py") else ""


def _context_fingerprint(context: list[dict[str, Any]]) -> str:
    evidence = [{"path": item["path"], "exists": item["exists"], "target": item["target"], "content_sha256": hashlib.sha256(item["content"].encode("utf-8")).hexdigest()} for item in context]
    return hashlib.sha256(json.dumps(evidence, sort_keys=True).encode("utf-8")).hexdigest()


def _reusable(value: dict[str, Any], mission_id: str, plan_id: Any, breakdown_id: Any, context_fingerprint: str) -> bool:
    return value.get("change_set_status") == "change_set_ready" and value.get("mission_id") == mission_id and value.get("source_plan_id") == plan_id and value.get("engineering_breakdown_id") == breakdown_id and value.get("repository_context_fingerprint") == context_fingerprint and bool(value.get("files"))


def _attempt_diagnostic(generated: dict[str, Any], checks: list[dict[str, Any]], output_text: str, attempt_number: int) -> dict[str, Any]:
    output_hash = hashlib.sha256(output_text.encode("utf-8")).hexdigest()
    raw_files = generated.get("files") if isinstance(generated.get("files"), list) else []
    candidates = []
    for index, item in enumerate(raw_files):
        if not isinstance(item, dict):
            candidates.append({"candidate_index": index, "path": None, "operation": None})
            continue
        candidates.append({
            "candidate_index": index,
            "path": str(item.get("path") or "").strip() or None,
            "operation": str(item.get("operation") or "").strip().lower() or None,
        })
    return {
        "attempt_number": attempt_number,
        "attempt_id": f"CHANGESET-{attempt_number}-{output_hash[:12].upper()}",
        "output_sha256": output_hash,
        "candidate_files": candidates,
        "failed_checks": [{key: value for key, value in check.items() if key != "passed"} for check in checks if not check["passed"]],
        "passed": all(check["passed"] for check in checks),
        "candidate_content_retained": False,
    }


def _parse_diagnostic(output_text: str, reason: str, attempt_number: int) -> dict[str, Any]:
    output_hash = hashlib.sha256(output_text.encode("utf-8")).hexdigest()
    check_name = "json_parse" if "JSON" in reason else "root_schema"
    return {
        "attempt_number": attempt_number,
        "attempt_id": f"CHANGESET-{attempt_number}-{output_hash[:12].upper()}",
        "output_sha256": output_hash,
        "candidate_files": [],
        "failed_checks": [{"name": check_name, "reason": reason, "path": None, "operation": None, "candidate_index": None}],
        "passed": False,
        "candidate_content_retained": False,
    }


def _blocked(
    mission_id: str | None,
    reason: str,
    plan: dict[str, Any] | None = None,
    handoff: dict[str, Any] | None = None,
    evidence: Any = None,
    *,
    diagnostics: list[dict[str, Any]] | None = None,
    repair_attempt_count: int = 0,
) -> dict[str, Any]:
    diagnostic_evidence = diagnostics if diagnostics is not None else evidence
    remaining = diagnostics[-1]["failed_checks"] if diagnostics else []
    return {
        "mission_id": mission_id,
        "change_set_status": "blocked",
        "source_plan_id": (plan or {}).get("plan_id"),
        "engineering_breakdown_id": (handoff or {}).get("breakdown_id"),
        "files": [],
        "validation": {"status": "not-passed", "evidence": diagnostic_evidence, "remaining_failed_checks": remaining},
        "generation": {"repair_attempt_count": repair_attempt_count, "attempts": diagnostics or [], "raw_output_exposed": False},
        "assumptions": [],
        "risks": [],
        "blocked_stage": "executable_change_set",
        "blocked_reason": reason,
        "next_action": "Retry executable change-set generation after reviewing validation errors.",
        "approval_required": "none",
        "governance": {"repository_mutation": False, "branch_creation": False, "commit": False, "push": False, "pull_request": False, "merge": False, "deployment": False},
    }


def _check(
    name: str,
    passed: bool,
    reason: str,
    *,
    path: str | None = None,
    operation: str | None = None,
    candidate_index: int | None = None,
) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "reason": reason, "path": path, "operation": operation, "candidate_index": candidate_index}


def _string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []
