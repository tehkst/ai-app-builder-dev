"""Structured handoffs between employees (adapted from the NEXUS handoff templates in
agency-agents, MIT): what each employee is given, and the shape of what it must hand back."""
from __future__ import annotations

from typing import Any, Dict, List

from app.platform.orca.execution_policy import ALLOWED_FORMS, check_command_allowed
from app.platform.orca.models import MAX_ATTEMPTS, Mission, Task

MAX_PLANNED_TASKS = 8
SPECIALTIES = ("general", "backend", "frontend", "php", "database", "upgrade", "devops", "docs")
SPECIALTY_GUIDE = (
    "frontend for anything users see or interact with (pages, components, forms, styles); php for PHP, "
    "WordPress, WooCommerce or Laravel code; database for schema changes, migrations, data fixes and "
    "query performance; upgrade for moving a language, framework or package to a newer version; devops "
    "for CI, Docker, build and deployment configuration; docs for README, setup guides and other "
    "documentation; backend for other APIs, data and server logic; general otherwise"
)
CHECK_OUTPUT_CHARS = 3_000
PROMPT_DIFF_CHARS = 40_000  # diff shown to reviewers and the writer

_STRING_LIST = {"type": "array", "items": {"type": "string"}}

PLAN_SCHEMA: Dict[str, Any] = {
    "type": "object", "required": ["summary", "tasks"],
    "properties": {
        "summary": {"type": "string"},
        "tasks": {"type": "array", "items": {
            "type": "object", "required": ["title", "description", "specialty", "acceptance_checks"],
            "properties": {"title": {"type": "string"}, "description": {"type": "string"},
                           "specialty": {"type": "string", "enum": list(SPECIALTIES)},
                           "user_facing": {"type": "boolean"},
                           "depends_on": {"type": "array", "items": {"type": "integer"}},
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
        "likely files, a specialty (" + SPECIALTY_GUIDE + "), user_facing (true if people see or use "
        "the result: a page, form, email or message, whatever the specialty), depends_on (the numbers of "
        "earlier tasks it needs; leave it out to wait for the task before it, or give [] when it can be "
        "built at the same time as others; tasks only run side by side when their files don't overlap, "
        "so list every file each task will change) and at least one "
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
        if task.get("specialty") not in SPECIALTIES:  # routes the task and decides whether UX review applies
            problems.append(f"task {index} ({task.get('title')}) needs a specialty: one of {', '.join(SPECIALTIES)}")
        deps = task.get("depends_on")
        if deps is not None and any(not isinstance(d, int) or isinstance(d, bool) or not 1 <= d < index for d in deps):
            problems.append(f"task {index} ({task.get('title')}) depends_on must list numbers of earlier tasks (1 to {index - 1})")
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
    def line(i: Dict[str, Any]) -> str:
        extra = "".join(f" ({k}: {i[k]})" for k in ("location", "fix") if i.get(k))
        return f"- [{i.get('severity')}] {i.get('detail')}{extra}"
    return "\n".join(line(i) for i in issues) or "- (none listed)"


def _changes_block(changes: Dict[str, Any]) -> str:
    """The real change set (from the baseline history, not the builder's claim)."""
    files = "\n".join(f"- {f['path'] if isinstance(f, dict) else f}" for f in changes.get("files") or []) or "- (no changes)"
    diff = changes.get("diff") or ""
    cut = " (cut short)" if changes.get("truncated") or len(diff) > PROMPT_DIFF_CHARS else ""
    diff = diff[:PROMPT_DIFF_CHARS]
    return (f"## Every file changed so far, compared with the client's code as received\n{files}\n\n"
            f"## The diff{cut}\n```diff\n{diff}\n```\n")


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
    security = task.latest_security_feedback()
    if security:
        parts.append("## Security review of your previous attempt: FAIL (QA had passed it)\n" + security.get("evidence", "") +
                     "\n\nIssues to fix:\n" + _issues_block(security.get("issues") or []) + "\n")
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


SECURITY_SEVERITIES = ("critical", "high", "medium", "low")
BLOCKING_SECURITY = ("critical", "high")
SECURITY_SCHEMA: Dict[str, Any] = {
    "type": "object", "required": ["verdict", "evidence", "issues"],
    "properties": {
        "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
        "evidence": {"type": "string"},
        "issues": {"type": "array", "items": {
            "type": "object", "required": ["severity", "detail"],
            "properties": {"severity": {"type": "string", "enum": list(SECURITY_SEVERITIES)},
                           "detail": {"type": "string"}, "location": {"type": "string"}, "fix": {"type": "string"}},
        }},
    },
}


def security_review_assignment(mission: Mission, task: Task, build: Dict[str, Any], qa: Dict[str, Any],
                               changes: Dict[str, Any]) -> str:
    return (f"## Mission context\n{mission.goal}\n\n{_task_block(task)}\n{_scope_block(mission, task)}\n"
            f"## Builder handoff (attempt {task.attempts})\n{build.get('summary', '')}\n\n"
            f"## QA verdict: PASS\n{qa.get('evidence', '')}\n\n{_changes_block(changes)}\n"
            "## Deliverable\nThis change goes to a client. Review every changed file above (the list comes from "
            "the real diff, so check all of it, not only what the builder mentioned) and what it touches, for "
            "security problems the change introduces or leaves exposed. Call final_output with verdict (FAIL if "
            "any critical or high issue), evidence and issues (severity critical/high/medium/low, detail: how it "
            "could be abused, location, fix).")


HANDOVER_SCHEMA: Dict[str, Any] = {
    "type": "object", "required": ["summary", "changes", "how_to_test", "watch_out"],
    "properties": {"summary": {"type": "string"}, "changes": _STRING_LIST, "how_to_test": _STRING_LIST,
                   "watch_out": _STRING_LIST},
}


def handover_assignment(mission: Mission, changes: Dict[str, Any]) -> str:
    tasks = []
    for t in mission.tasks:
        builds = [h for h in t.handoffs if h.get("kind") == "build"]
        did = f"\n  Builder's summary: {builds[-1].get('summary', '')}" if builds else ""
        tasks.append(f"- {t.title} ({t.status}): {t.description}{did}")
    verified = ("Every acceptance check passed in an isolated test environment:\n" +
                "\n".join(f"- `{c}`" for t in mission.tasks for c in t.acceptance_checks)
                if mission.status == "complete" else "The project's tests were NOT run for this work.")
    return (f"## The client asked for\n{mission.goal}\n\n## Plan\n{mission.plan_summary}\n\n## Tasks\n" + "\n".join(tasks) +
            f"\n\n{_changes_block(changes)}\n## Verification\n{verified}\n\n"
            "## Deliverable\nWrite the handover for the client (a small-business owner, not a developer). "
            "Describe only what the diff above actually changes. Call final_output with: summary (2-3 plain "
            "sentences), changes (one line per change, in their terms), how_to_test (steps they can follow in "
            "their app), watch_out (anything they must do or know, including what was not tested; may be empty).")
