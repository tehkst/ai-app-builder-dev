"""Structured handoffs between employees (adapted from the NEXUS handoff templates in
agency-agents, MIT): what each employee is given, and the shape of what it must hand back."""
from __future__ import annotations

from typing import Any, Dict, List

from app.platform.orca.execution_policy import ALLOWED_FORMS, check_command_allowed
from app.platform.orca.models import MAX_ATTEMPTS, Mission, Task

MAX_PLANNED_TASKS = 8
SPECIALTIES = ("general", "backend", "frontend")
CHECK_OUTPUT_CHARS = 3_000

_STRING_LIST = {"type": "array", "items": {"type": "string"}}

PLAN_SCHEMA: Dict[str, Any] = {
    "type": "object", "required": ["summary", "tasks"],
    "properties": {
        "summary": {"type": "string"},
        "tasks": {"type": "array", "items": {
            "type": "object", "required": ["title", "description", "acceptance_checks"],
            "properties": {"title": {"type": "string"}, "description": {"type": "string"},
                           "specialty": {"type": "string", "enum": list(SPECIALTIES)},
                           "files": _STRING_LIST, "acceptance_checks": _STRING_LIST},
        }},
    },
}
BUILD_SCHEMA: Dict[str, Any] = {
    "type": "object", "required": ["summary", "files_changed"],
    "properties": {"summary": {"type": "string"}, "files_changed": _STRING_LIST},
}
VERDICT_SCHEMA: Dict[str, Any] = {
    "type": "object", "required": ["verdict", "evidence", "issues"],
    "properties": {
        "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
        "evidence": {"type": "string"},
        "issues": {"type": "array", "items": {
            "type": "object", "required": ["severity", "detail"],
            "properties": {"severity": {"type": "string", "enum": ["blocker", "suggestion", "nit"]},
                           "detail": {"type": "string"}},
        }},
    },
}


def plan_assignment(mission: Mission) -> str:
    return (
        "## Mission\n" + mission.goal + "\n\n"
        "## Deliverable\nInspect the workspace, then call final_output with a summary of your approach "
        f"and an ordered task list (at most {MAX_PLANNED_TASKS} tasks), each with title, description, "
        "likely files, a specialty (frontend for anything users see or interact with: pages, components, "
        "forms, styles; backend for APIs, data and server logic; general otherwise) and at least one "
        "acceptance check (a single command that exits 0 only when the task is done). Allowed check "
        "forms: " + ALLOWED_FORMS + "."
    )


def plan_problems(planned: List[Dict[str, Any]], workspace_root: str) -> List[str]:
    """Reasons a plan can't be accepted (empty means OK): every task needs a check, and every check
    must pass Orca's execution policy so it can actually be run once execution is approved."""
    if not planned:
        return ["the plan has no tasks"]
    if len(planned) > MAX_PLANNED_TASKS:
        return [f"the plan has {len(planned)} tasks; the maximum is {MAX_PLANNED_TASKS}"]
    problems = []
    for index, task in enumerate(planned, start=1):
        checks = [c for c in task.get("acceptance_checks") or [] if str(c).strip()]
        if not checks:
            problems.append(f"task {index} ({task.get('title')}) has no acceptance check")
        for check in checks:
            allowed, reason = check_command_allowed(check, workspace_root)
            if not allowed:
                problems.append(f"task {index} check `{check}` is not allowed: {reason}")
    return problems


def _task_block(task: Task) -> str:
    checks = "\n".join(f"- `{c}`" for c in task.acceptance_checks) or "- (none)"
    files = ", ".join(task.files) or "(not specified)"
    return (f"## Task: {task.title}\n{task.description}\n\nSpecialty: {task.specialty}\nLikely files: {files}\n\n"
            f"## Acceptance checks\n{checks}\n")


def _scope_block(mission: Mission, task: Task) -> str:
    """The other tasks in the plan, so neither builder nor QA pulls their work into this task
    (first live mission: QA failed T1 for lacking a test that T2 was planned to add)."""
    others = [f"- {t.task_id} ({t.status}): {t.title}" for t in mission.tasks if t.task_id != task.task_id]
    if not others:
        return ""
    return ("## Scope\nThis task is " + task.task_id + ". These belong to OTHER tasks of the mission; "
            "don't do them here, and don't treat them as missing from this task:\n" + "\n".join(others) + "\n")


def _issues_block(issues: List[Dict[str, Any]]) -> str:
    return "\n".join(f"- [{i.get('severity')}] {i.get('detail')}" for i in issues) or "- (none listed)"


def build_assignment(mission: Mission, task: Task) -> str:
    parts = [f"## Mission context\n{mission.goal}\n\nPlan summary: {mission.plan_summary}\n",
             _task_block(task), _scope_block(mission, task), f"## Attempt\n{task.attempts} of {MAX_ATTEMPTS}\n"]
    feedback = task.latest_qa_feedback()
    if feedback:
        parts.append("## QA verdict on your previous attempt: FAIL\n" + feedback.get("evidence", "") +
                     "\n\nIssues to fix:\n" + _issues_block(feedback.get("issues") or []) + "\n")
        failed_checks = [c for c in feedback.get("check_results") or [] if not c.get("passed")]
        for check in failed_checks:
            parts.append(f"Failed check `{check['command']}` (exit {check['exit_code']}):\n{check['output']}\n")
    ux = task.latest_ux_feedback()
    if ux:
        parts.append("## UX review of your previous attempt: FAIL (QA had passed it)\n" + ux.get("evidence", "") +
                     "\n\nIssues to fix:\n" + _issues_block(ux.get("issues") or []) + "\n")
    parts.append("## Deliverable\nImplement the task, then call final_output with a summary and files_changed.")
    return "\n".join(parts)


def review_assignment(mission: Mission, task: Task, build: Dict[str, Any],
                      check_results: List[Dict[str, Any]], checks_executed: bool) -> str:
    if checks_executed:
        lines = [f"- `{c['command']}` -> {'PASS' if c['passed'] else 'FAIL'} (exit {c['exit_code']})\n"
                 f"  {c['output'][-CHECK_OUTPUT_CHARS:]}" for c in check_results]
        checks = "\n".join(lines) or "- (task has no acceptance checks)"
    else:
        checks = ("- Not executed: the founder has not approved code execution for this mission. "
                  "Judge by reading the files; you cannot rely on runtime evidence.")
    return (f"## Mission context\n{mission.goal}\n\n{_task_block(task)}\n{_scope_block(mission, task)}\n"
            f"## Builder handoff (attempt {task.attempts})\n{build.get('summary', '')}\n"
            f"Files changed: {', '.join(build.get('files_changed') or []) or '(none listed)'}\n\n"
            f"## Acceptance check results\n{checks}\n\n"
            "## Deliverable\nRead the changed files and call final_output with verdict, evidence and issues.")


def ux_review_assignment(mission: Mission, task: Task, build: Dict[str, Any], qa: Dict[str, Any]) -> str:
    return (f"## Mission context\n{mission.goal}\n\n{_task_block(task)}\n{_scope_block(mission, task)}\n"
            f"## Builder handoff (attempt {task.attempts})\n{build.get('summary', '')}\n"
            f"Files changed: {', '.join(build.get('files_changed') or []) or '(none listed)'}\n\n"
            f"## QA verdict: PASS\n{qa.get('evidence', '')}\n\n"
            "## Deliverable\nRead the changed interface files, walk through them as a first-time user, and "
            "call final_output with verdict, evidence and issues.")
