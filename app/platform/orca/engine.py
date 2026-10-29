"""Orca: the orchestrator that runs missions with AI employees.

Orca itself is deterministic code (so the process is predictable and auditable); the employees
do the thinking on Nautilus. Pipeline (adapted from NEXUS): the architect plans; each task goes
through a Dev↔QA loop (builder, acceptance checks, QA verdict; FAIL returns to the builder with
the findings; MAX_ATTEMPTS then escalate); an integration gate re-runs every check. State is
saved after every step, so a mission resumes after a restart.

Executing generated code (acceptance checks, builder commands) requires the founder's approval
for the mission; without it, Orca still plans, builds and reviews, but finishes
`complete_unverified`.

Client missions (`sandboxed=True`, started from Mission Control -> Clients) work on a disposable copy
of a client's code inside `client_base`, and every command runs in the container sandbox
(`sandbox_commands.py`); dependencies are installed there once execution is approved.
"""
from __future__ import annotations

import json
import os
import posixpath
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.platform.nautilus.messages import ChatFn
from app.platform.orca import cancel, gates, handoffs, sandbox_commands
from app.platform.orca.employee_runner import run_employee
from app.platform.orca.models import MAX_ATTEMPTS, Mission, Task
from app.platform.orca.store import DbMissionStore, MissionStore
from app.platform.orca.workforce import Employee, Workforce, WorkforceError, load_workforce
from app.platform.services.nautilus_repair_service.sandbox import within_approved_base

MAX_STEPS_PER_RUN = 200
MAX_PARALLEL = 3  # tasks built side by side at most
MAX_SAVED_CONVERSATION_BYTES = 4_000_000  # a paused planner conversation bigger than this restarts instead


def _norm(path: str, workspace_root: str = "") -> str:
    """A file's identity for overlap checks: resolved inside the workspace (so symlink aliases match)
    and case-folded (macOS treats Cart.php and cart.php as one file; folding elsewhere only makes
    tasks wait for each other, which is safe)."""
    if not path:
        return ""
    clean = posixpath.normpath(str(path).replace("\\", "/")).lstrip("/")
    if workspace_root:
        root = os.path.realpath(workspace_root)
        resolved = os.path.realpath(os.path.join(root, clean))
        if resolved == root or resolved.startswith(root + os.sep):
            clean = os.path.relpath(resolved, root).replace(os.sep, "/")
    return clean.casefold()


def _fits(messages: List[Dict[str, Any]]) -> bool:
    """Whether a paused conversation is small enough to keep in the mission (else planning restarts)."""
    try:
        return len(json.dumps(messages)) <= MAX_SAVED_CONVERSATION_BYTES
    except (TypeError, ValueError):
        return False


def safe_command(command: str, workspace_root: str) -> str:
    """What the activity feed may store for a command: an allowed command (test runners, read-only
    inspection) with secret patterns removed; anything else only by its program name, since a
    model-written command could carry a credential or a fragment of source."""
    from app.platform.clients.redaction import redact
    from app.platform.orca.execution_policy import check_command_allowed

    command = str(command or "")
    if command and check_command_allowed(command, workspace_root)[0]:
        return redact(command)[:160]
    program = command.strip().split(" ", 1)[0][:40]
    return f"{program} (a command that isn't allowed)" if program else "a command"
STATUS_LINES = {"awaiting_execution_approval": "waiting for your OK to run the code", "paused": "paused",
                "awaiting_decision": "waiting for the client's decisions before planning",
                "complete": "done: everything checked", "complete_unverified": "done, but not everything could be checked",
                "escalated": "stuck: needs you", "failed": "stopped: it couldn't plan the work",
                "cancelled": "cancelled by you"}


class Orca:
    def __init__(self, *, chat: Optional[ChatFn] = None, workforce: Optional[Workforce] = None,
                 store: Optional[MissionStore] = None, sandbox_base: Optional[Path] = None) -> None:
        self._chat = chat
        self.workforce = workforce or load_workforce()
        self.store = store or DbMissionStore()
        self.sandbox_base = sandbox_base
        self._pinned_chats: Dict[Tuple[str, Optional[str]], ChatFn] = {}
        self._mission_lock = threading.RLock()  # parallel tasks update one mission
        self._command_locks: Dict[str, threading.Lock] = {}

    @property
    def chat(self) -> ChatFn:
        if self._chat is None:
            from app.platform.nautilus.chat_providers import build_chat_fn
            from app.platform.persistence.database import create_platform_tables

            create_platform_tables()  # provider selection reads the runtime settings table
            self._chat = build_chat_fn()
        return self._chat

    # ---- founder-facing operations -----------------------------------------------------

    def _chat_for(self, mission: Mission, employee: Optional[Employee] = None) -> ChatFn:
        return cancel.stoppable(mission.mission_id, self._model_for(mission, employee))

    def _model_for(self, mission: Mission, employee: Optional[Employee] = None) -> ChatFn:
        """The model an employee works with. A client mission always uses exactly the provider and
        model the client agreed to (no tiers: consent names one model). Other missions follow the
        employee's model_tier within the selected provider (company/ai-pricing.yaml). An injected
        chat, in checks, wins."""
        if self._chat is not None:
            return self._chat
        tier = employee.model_tier if employee else "standard"
        if mission.ai_provider:
            key = (mission.ai_provider, mission.ai_model or "")
            if key not in self._pinned_chats:
                from app.platform.nautilus.chat_providers import build_chat_fn

                self._pinned_chats[key] = build_chat_fn(*key)
            return self._pinned_chats[key]
        if tier == "standard":
            return self.chat
        from app.platform.persistence.database import create_platform_tables
        from app.platform.runtime.provider_router import default_model, selected_provider

        create_platform_tables()
        provider = selected_provider()
        model = default_model(provider)
        from app.platform.ai_costs import model_for_tier

        key = (provider, model_for_tier(provider, model, tier))
        if key not in self._pinned_chats:
            from app.platform.nautilus.chat_providers import build_chat_fn

            self._pinned_chats[key] = build_chat_fn(*key)
        return self._pinned_chats[key]

    def start_mission(self, goal: str, workspace_root: str, *, execution_approved: bool = False,
                      client: Optional[Dict[str, Any]] = None, client_base: Optional[Path] = None,
                      ai: Optional[Tuple[str, str]] = None, baseline_dir: Optional[str] = None) -> Mission:
        """`client` + `client_base` start a sandboxed client mission: the workspace must be inside
        `client_base` (the client-mission area), never the generated-app sandbox. Client missions
        must name the consented AI provider and model (`ai`), which every later run uses."""
        workspace = Path(workspace_root).resolve()
        if not goal.strip():
            raise ValueError("A mission needs a goal.")
        if (client is None) != (client_base is None) or (client is not None and not ai):
            raise ValueError("A client mission needs the client, its workspace area and the agreed AI provider.")
        base = client_base if client is not None else self.sandbox_base
        if not workspace.is_dir() or not within_approved_base(workspace, base):
            raise ValueError("Mission workspace must be an existing directory inside the approved sandbox base.")
        if baseline_dir is not None:  # the history folder: in the client area, never inside the copy
            history = Path(baseline_dir).resolve()
            if client is None or not within_approved_base(history, base) or workspace in (history, *history.parents):
                raise ValueError("The baseline history must sit next to the client copy, not inside it.")
        mission = Mission("ORCA-" + uuid.uuid4().hex[:12].upper(), goal.strip(), str(workspace),
                          execution_approval="approved" if execution_approved else "pending",
                          sandboxed=client is not None, client=dict(client) if client else None,
                          ai_provider=ai[0] if client is not None else None, ai_model=ai[1] if client is not None else None,
                          baseline_dir=str(Path(baseline_dir).resolve()) if baseline_dir else None)
        mission.record("mission_started", execution_approval=mission.execution_approval)
        self.store.save(mission)
        return mission

    def decide_execution(self, mission_id: str, *, approved: bool, decided_by: str = "founder") -> Mission:
        mission = self._load(mission_id)
        if mission.status != "awaiting_execution_approval":
            raise ValueError(f"Mission is '{mission.status}', not awaiting an execution decision.")
        mission.execution_approval = "approved" if approved else "declined"
        mission.status = "building"
        mission.record("execution_decided", approved=approved, decided_by=decided_by)
        self.store.save(mission)
        return mission

    def answer_questions(self, mission_id: str, answers: List[str], *, decided_by: str = "founder") -> Mission:
        """The founder (with the client) answers the team's questions. The architect then plans again with
        the decisions: finished tasks are kept, unfinished ones are re-planned, because an answer can
        change the work itself (the test drive: "verify the member by email" needs server code that the
        original pricing-only task was not allowed to touch)."""
        mission = self._load(mission_id)
        if mission.status != "awaiting_decision" or not mission.questions:
            raise ValueError(f"Mission is '{mission.status}', not waiting for decisions.")
        cleaned = [str(a or "").strip() for a in answers or []]
        if len(cleaned) != len(mission.questions) or not all(cleaned):
            raise ValueError("Answer every question.")
        if any(len(a) > 2000 for a in cleaned):
            raise ValueError("Keep each answer under 2,000 characters.")
        mission.answers.extend({"question": q, "answer": a} for q, a in zip(mission.questions, cleaned))
        unfinished = [t for t in mission.tasks if t.status != "passed"]
        mission.tasks = [t for t in mission.tasks if t.status == "passed"]
        mission.questions, mission.status = [], "planning"
        mission.record("questions_answered", decided_by=decided_by, count=len(cleaned),
                       replanned=[{"task": t.task_id, "title": t.title, "attempts": t.attempts} for t in unfinished])
        self.store.save(mission)
        return mission

    def retry_task(self, mission_id: str, *, decided_by: str = "founder",
                   acceptance_checks: Optional[List[str]] = None) -> Mission:
        """Founder override: give an escalated task a fresh set of Dev↔QA attempts, optionally with
        new acceptance checks (e.g. the planned one needed a database the sandbox doesn't have)."""
        mission = self._load(mission_id)
        task = next((t for t in mission.tasks if t.status == "escalated"), None)
        if mission.status != "escalated" or task is None:
            raise ValueError("Only a mission escalated on a task can be retried.")
        if acceptance_checks is not None:
            from app.platform.orca.execution_policy import check_command_allowed

            checks = [str(c).strip() for c in acceptance_checks if str(c).strip()]
            if not checks:
                raise ValueError("Give at least one acceptance check.")
            for check in checks:
                allowed, reason = check_command_allowed(check, mission.workspace_root)
                if not allowed:
                    raise ValueError(f"Check `{check}` is not allowed: {reason}")
            mission.record("checks_replaced", task=task.task_id, decided_by=decided_by,
                           old=task.acceptance_checks, new=checks)
            task.acceptance_checks = checks
        task.status, task.attempts = "pending", 0
        mission.status, mission.escalation = "building", None
        if mission.dependencies is not None and not any(d.get("passed") for d in mission.dependencies):
            mission.dependencies = None  # the install failed (e.g. Docker was down): try it again first
        mission.record("task_retried", task=task.task_id, decided_by=decided_by)
        self.store.save(mission)
        return mission

    def run(self, mission_id: str, max_steps: int = MAX_STEPS_PER_RUN) -> Mission:
        """Advance the mission until it finishes, waits for the founder, pauses on a provider
        error, or max_steps is hit. Running a paused mission resumes it."""
        mission = self._load(mission_id)
        if mission.status == "paused":
            mission.status, mission.resume_status = mission.resume_status or "building", None
            mission.record("resumed", after=mission.paused_reason)
            mission.paused_reason = None
        started_as = mission.status
        for _ in range(max_steps):
            if cancel.requested(mission.mission_id):
                self._cancel(mission, cancel.requested_by(mission.mission_id))
                self.store.save(mission)
            if mission.finished or mission.status in ("awaiting_execution_approval", "awaiting_decision", "paused"):
                break
            self._step(mission)
            self.store.save(mission)
        if cancel.requested(mission.mission_id):
            self._cancel(mission, cancel.requested_by(mission.mission_id))
            self.store.save(mission)
        if mission.status != started_as:
            self._activity(mission, "Orca", "status", STATUS_LINES.get(mission.status, mission.status))
        return mission

    def cancel_mission(self, mission_id: str, *, decided_by: str = "founder") -> Mission:
        """Founder: stop a mission that isn't running (a running one is stopped through `cancel.request`)."""
        mission = self._load(mission_id)
        if mission.status in ("complete", "complete_unverified", "cancelled"):
            raise ValueError(f"Mission is already {mission.status}.")
        self._cancel(mission, decided_by)
        self.store.save(mission)
        self._activity(mission, "Orca", "status", STATUS_LINES["cancelled"])
        return mission

    def _cancel(self, mission: Mission, decided_by: str) -> None:
        cancel.clear(mission.mission_id)
        if mission.status in ("complete", "complete_unverified", "cancelled"):
            return  # it finished before the request was seen
        with self._mission_lock:
            mission.record("cancelled", decided_by=decided_by, was=mission.status)
            mission.status, mission.resume_status, mission.paused_reason = "cancelled", None, None
            mission.plan_progress = None

    def _pause(self, mission: Mission, employee: str, error: Optional[str], reason: Optional[str] = None) -> None:
        """The AI provider failed (missing key, outage, timeout), or the sandbox isn't available:
        that's not the employee's fault, so pause instead of failing or using up an attempt."""
        if cancel.requested(mission.mission_id):
            return  # the employee stopped because the founder cancelled: `run` records that
        with self._mission_lock:
            if mission.status != "paused":  # a task running side by side may have paused it already
                mission.resume_status, mission.status = mission.status, "paused"
                mission.paused_reason = reason or f"AI provider error while {employee} was working: {error or 'unknown error'}"
                mission.record("paused", employee=employee, error=error)

    def _load(self, mission_id: str) -> Mission:
        mission = self.store.load(mission_id)
        if mission is None:
            raise ValueError(f"Mission '{mission_id}' not found.")
        return mission

    # ---- pipeline ----------------------------------------------------------------------

    def _step(self, mission: Mission) -> None:
        if mission.status == "planning":
            self._plan(mission)
        elif mission.status == "building":
            if mission.sandboxed and mission.execution_allowed and mission.dependencies is None:
                self._install_dependencies(mission)
                return
            pending = [t for t in mission.tasks if t.status == "pending"]
            if not pending:
                stuck = next((t for t in mission.tasks if t.status != "passed"), None)
                if stuck is not None:  # e.g. two tasks escalated side by side and only one was retried
                    mission.status = "escalated"
                    mission.escalation = {"reason": f"Task {stuck.task_id} is still stuck after an earlier escalation.",
                                          "task": stuck.task_id, "attempts": stuck.handoffs}
                    mission.record("escalated", task=stuck.task_id)
                    return
                mission.status = "integration"
                return
            batch = self._batch(mission, pending)
            if len(batch) == 1:
                self._work_task(mission, batch[0])
            else:
                self._work_parallel(mission, batch)
        elif mission.status == "integration":
            gates.integrate(mission)
            if mission.sandboxed and mission.status in ("complete", "complete_unverified") and mission.handover is None:
                self._handover(mission)

    def _activity(self, mission: Mission, who: str, kind: str, detail: str) -> None:
        """One line of live progress; never allowed to break the mission."""
        try:
            self.store.record_activity(mission.mission_id, who, kind, detail)
        except Exception:
            pass

    def _watch(self, mission: Mission, employee: Employee, doing: str):
        """Record that an employee started, and turn its tool calls into progress lines."""
        self._activity(mission, employee.name, "started", doing)
        verbs = {"read_file": ("read", "reading"), "list_files": ("read", "looking through the files"),
                 "write_file": ("write", "writing"), "run_command": ("command", "running")}

        def on_event(event: str, payload: Dict[str, Any]) -> None:
            if event == "wrap_up":
                self._activity(mission, employee.name, "status", "out of turns: writing up what it has so far")
                return
            if event != "tool_call" or payload.get("name") not in verbs or payload.get("outcome") not in ("ok", "error", "denied"):
                return
            kind, verb = verbs[payload["name"]]
            target = payload.get("target") or ""
            if kind == "command":
                target = safe_command(target, mission.workspace_root)
            note = {"error": " (failed)", "denied": " (not allowed)"}.get(payload["outcome"], "")
            self._activity(mission, employee.name, kind, f"{verb} {target}".strip() + note)
        return on_event

    def _install_dependencies(self, mission: Mission) -> None:
        """Client missions: install packages in the sandbox before the first build (a failure is
        recorded, not fatal: the checks that need the packages will then fail visibly)."""
        if not sandbox_commands.sandbox_ready():
            # Found in the pilot: Docker wasn't reachable, every check failed with exit 125 and the
            # first task used up its attempts. Nothing can run, so wait for the founder instead.
            self._pause(mission, "sandbox", "Docker is not running",
                        reason="Docker isn't running and didn't start, so the client's code can't be run safely. Start Docker Desktop, then resume.")
            return
        self._activity(mission, "Orca", "command", "installing the project's packages in the sandbox")
        mission.dependencies = sandbox_commands.install_dependencies(mission.workspace_root)
        for d in mission.dependencies:
            self._activity(mission, "Orca", "check", f"{d['stack']} packages: {'installed' if d['passed'] else 'install failed'}")
        mission.record("dependencies_installed", stacks=[d["stack"] for d in mission.dependencies],
                       passed=all(d["passed"] for d in mission.dependencies))

    def _refresh_dependencies(self, mission: Mission, task: Task) -> List[Dict[str, Any]]:
        """The builder changed package.json (or requirements.txt): the project's own package manager
        rewrites the lockfile and reinstalls, so the checks test the new versions, not the old ones."""
        installed = [d.get("manifests") for d in mission.dependencies or [] if d.get("manifests")]
        if installed and installed[-1] == sandbox_commands.manifest_digest(mission.workspace_root):
            return []
        # No install has worked yet (e.g. the frozen install failed because package.json had already
        # changed in an earlier attempt): the update installs from the manifest as it is now.
        self._activity(mission, "Orca", "command", "package list changed: updating the lockfile and reinstalling (network on)")
        results = sandbox_commands.refresh_dependencies(mission.workspace_root)
        mission.dependencies = list(mission.dependencies or []) + results
        for d in results:
            updated = ", ".join(d.get("lockfiles_updated") or []) or "no lockfile change"
            self._activity(mission, "Orca", "check",
                           f"{d['stack']} packages: {'reinstalled (' + updated + ')' if d['passed'] else 'reinstall failed'}")
        mission.record("dependencies_refreshed", task=task.task_id, passed=all(d["passed"] for d in results),
                       lockfiles=[f for d in results for f in d.get("lockfiles_updated") or []])
        # A failed update shows as a failed check: QA sees it and the builder gets the package manager's error.
        return [{"command": d["command"], "passed": False, "exit_code": 1, "output": d["output"][-1500:]}
                for d in results if not d["passed"]]

    def _plan(self, mission: Mission) -> None:
        """The architect plans; a plan with problems gets one corrective round, then fails."""
        architect = self.workforce.for_responsibility("plan_mission")
        assignment, problems = handoffs.plan_assignment(mission), []
        for _ in range(2):
            earlier, mission.plan_progress = mission.plan_progress, None
            if earlier:
                mission.record("planning_resumed", employee=architect.employee_id, messages=len(earlier))
            result = run_employee(architect, assignment=assignment, workspace_root=mission.workspace_root,
                                  chat=self._chat_for(mission, architect), usage_sink=mission.usage,
                                  on_event=self._watch(mission, architect, "planning the work"),
                                  output_schema=handoffs.PLAN_SCHEMA,
                                  allow_writes=False, allow_execution=False,
                                  sandboxed=mission.sandboxed, resume_from=earlier)
            if result.run.status == "provider_error":
                self._pause(mission, architect.employee_id, result.run.error)
                if mission.status == "paused" and _fits(result.run.messages):
                    mission.plan_progress = result.run.messages  # resuming continues from here
                return
            questions = [str(q).strip()[:500] for q in (result.output or {}).get("open_questions") or [] if str(q).strip()]
            if questions and handoffs.answered_rounds(mission) < handoffs.MAX_QUESTION_ROUNDS:
                mission.questions, mission.status = questions[:8], "awaiting_decision"
                mission.plan_summary = str(result.output.get("summary") or "")
                mission.record("questions_asked", employee=architect.employee_id, questions=mission.questions)
                return
            planned = (result.output or {}).get("tasks") or []
            problems = handoffs.plan_problems(planned, mission.workspace_root, mission.sandboxed) if result.output else \
                [self._no_plan_reason(result.run)]
            if not problems:
                break
            assignment = handoffs.plan_assignment(mission) + "\n\n## Your previous plan was rejected\n" + \
                "\n".join(f"- {p}" for p in problems) + "\nFix these and submit the whole plan again."
        if problems:
            mission.status = "failed"
            mission.record("planning_failed", employee=architect.employee_id, problems=problems)
            return
        mission.plan_summary = result.output["summary"]
        kept = [t for t in mission.tasks if t.status == "passed"]  # re-planning after answers keeps finished work
        offset = max([int(t.task_id[1:]) for t in kept if t.task_id[1:].isdigit()] or [0])
        mission.tasks = kept + [Task(f"T{offset + i}", t["title"], t["description"], list(t.get("files") or []),
                                     [c for c in t["acceptance_checks"] if c.strip()],
                                     specialty=t.get("specialty") or "general",
                                     user_facing=bool(t.get("user_facing")) or t.get("specialty") == "frontend",
                                     # no depends_on given: wait for the task before it (the safe, sequential default)
                                     depends_on=[f"T{offset + d}" for d in t["depends_on"]]
                                     if handoffs.valid_depends_on(t.get("depends_on"), i)
                                     else ([f"T{offset + i - 1}"] if i > 1 else []))
                                for i, t in enumerate(planned, start=1)]
        waiting = mission.execution_approval == "pending"  # every task has checks to run
        mission.status = "awaiting_execution_approval" if waiting else "building"
        mission.record("planned", employee=architect.employee_id, tasks=len(mission.tasks),
                       awaiting_execution_approval=waiting)

    @staticmethod
    def _no_plan_reason(run) -> str:
        """Why no plan arrived, including the schema error if a submission was rejected."""
        rejected = [r.detail for r in run.tool_calls if r.name == "final_output" and r.outcome == "error"]
        reason = f"no plan was submitted ({run.status}{': ' + run.error if run.error else ''})"
        return reason + (f"; last submission rejected: {rejected[-1]}" if rejected else "")

    def _escalate_task(self, mission: Mission, task: Task, reason: str) -> None:
        with self._mission_lock:
            task.status, mission.status = "escalated", "escalated"
            if mission.escalation is None:  # the first stuck task is the one the founder sees
                mission.escalation = {"reason": reason, "task": task.task_id, "attempts": task.handoffs}
            mission.record("escalated", task=task.task_id)

    # ---- parallel tasks (step 5c) ------------------------------------------------------------

    def _batch(self, mission: Mission, pending: List[Task]) -> List[Task]:
        """The next tasks to build: ready ones (everything they depend on passed) that can run side
        by side - each lists its files and none overlap - up to MAX_PARALLEL. Otherwise one task."""
        passed = {t.task_id for t in mission.tasks if t.status == "passed"}
        ready = [t for t in pending if all(d in passed for d in t.depends_on)] or pending[:1]
        root = mission.workspace_root
        batch, claimed = [ready[0]], set(_norm(f, root) for f in ready[0].files)
        if not claimed:
            return batch
        for task in ready[1:]:
            files = set(_norm(f, root) for f in task.files)
            if len(batch) >= MAX_PARALLEL:
                break
            if files and not files & claimed:
                batch.append(task)
                claimed |= files
        return batch

    def _work_parallel(self, mission: Mission, batch: List[Task]) -> None:
        ids = [t.task_id for t in batch]
        mission.record("parallel_batch", tasks=ids)
        self._activity(mission, "Orca", "started", f"building {', '.join(ids)} side by side")
        errors: List[BaseException] = []

        def work(task: Task) -> None:
            others = {_norm(f, mission.workspace_root) for t in batch if t is not task for f in t.files}
            try:
                self._work_task(mission, task, off_limits=others)
            except BaseException as exc:  # re-raised below so the runner records the crash
                errors.append(exc)

        threads = [threading.Thread(target=work, args=(t,), name=f"orca-{mission.mission_id}-{t.task_id}") for t in batch]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        if errors:
            raise errors[0]

    def _command_lock(self, mission: Mission) -> threading.Lock:
        return self._command_locks.setdefault(mission.workspace_root, threading.Lock())

    def _save(self, mission: Mission) -> None:
        with self._mission_lock:
            self.store.save(mission)

    def _work_task(self, mission: Mission, task: Task, off_limits: Optional[set] = None) -> None:
        """One Dev<->QA attempt. `off_limits`: files of tasks built side by side (never written here)."""
        parallel = off_limits is not None
        write_allowed = (lambda path: _norm(path, mission.workspace_root) not in off_limits) if parallel else None
        lock = self._command_lock(mission) if parallel and not mission.sandboxed else None
        if task.attempts >= MAX_ATTEMPTS:  # e.g. the process stopped during the last attempt
            self._escalate_task(mission, task, f"Task {task.task_id} used all {MAX_ATTEMPTS} attempts "
                                               "(the last one was interrupted).")
            return
        task.attempts += 1
        self._save(mission)  # an interrupted attempt still counts toward the limit
        builder = self.workforce.find(f"build_task:{task.specialty}") or self.workforce.for_responsibility("build_task")
        built = run_employee(builder, assignment=handoffs.build_assignment(mission, task),
                             workspace_root=mission.workspace_root, chat=self._chat_for(mission, builder),
                             on_event=self._watch(mission, builder, f"building {task.task_id}: {task.title} "
                                                                    f"(attempt {task.attempts})"),
                             usage_sink=mission.usage, output_schema=handoffs.BUILD_SCHEMA, allow_writes=True,
                             write_allowed=write_allowed, command_lock=lock,
                             allow_execution=mission.execution_allowed, sandboxed=mission.sandboxed)
        if built.run.status == "provider_error":
            task.attempts -= 1
            self._pause(mission, builder.employee_id, built.run.error)
            return
        build = built.output or {"summary": f"Builder produced no result ({built.run.status}).", "files_changed": []}
        task.handoffs.append({"kind": "build", "attempt": task.attempts, "employee": builder.employee_id, **build})

        refresh: List[Dict[str, Any]] = []
        if mission.sandboxed and mission.execution_allowed:
            with self._command_lock(mission):  # a task side by side must not test on a half-replaced install
                refresh = self._refresh_dependencies(mission, task)
        checks = refresh + gates.run_checks(mission, task.acceptance_checks, lock=lock)
        for check in checks:
            self._activity(mission, "Orca", "check",
                           f"{safe_command(check['command'], mission.workspace_root)}: {gates.outcome_word(check)}")
        qa = self.workforce.for_responsibility("review_task")
        reviewed = run_employee(qa, assignment=handoffs.review_assignment(mission, task, build, checks,
                                                                          mission.execution_allowed),
                                workspace_root=mission.workspace_root, chat=self._chat_for(mission, qa),
                                on_event=self._watch(mission, qa, f"reviewing {task.task_id}"),
                                usage_sink=mission.usage, output_schema=handoffs.VERDICT_SCHEMA, allow_writes=False,
                                allow_execution=False, sandboxed=mission.sandboxed)
        if reviewed.run.status == "provider_error":
            task.handoffs.pop()  # the build stays in the workspace; the attempt is redone in full
            task.attempts -= 1
            self._pause(mission, qa.employee_id, reviewed.run.error)
            return
        verdict = reviewed.output or {"verdict": "FAIL", "evidence": f"QA produced no verdict ({reviewed.run.status}).",
                                      "issues": [{"severity": "blocker", "detail": "No QA verdict was recorded."}]}
        blockers = [i for i in verdict.get("issues") or [] if i.get("severity") == "blocker"]
        passed = (verdict["verdict"] == "PASS" and not blockers and built.output is not None
                  and gates.checks_ok(checks) and not str(verdict.get("decision_needed") or "").strip())
        task.handoffs.append({"kind": "qa_verdict", "attempt": task.attempts, "employee": qa.employee_id,
                              **verdict, "verdict": "PASS" if passed else "FAIL", "check_results": checks})
        failed_by = None if passed else "QA"
        # After QA: user-facing tasks need the UX Designer's PASS, and every client task the Security
        # Reviewer's (mandatory: a missing reviewer fails closed).
        reviews = []
        if task.user_facing or task.specialty == "frontend":
            reviews.append(("ux_verdict", "review_ux", "UX review", handoffs.VERDICT_SCHEMA, handoffs.ux_blocker,
                            lambda: handoffs.ux_review_assignment(mission, task, build, verdict)))
        if mission.sandboxed:
            reviews.append(("security_verdict", "review_security", "security review", handoffs.SECURITY_SCHEMA,
                            handoffs.security_blocker,
                            lambda: handoffs.security_review_assignment(mission, task, build, verdict, self._changes(mission))))
        for kind, responsibility, label, schema, blocking, assignment in reviews:
            if not passed:
                break
            try:
                ok = self._extra_review(mission, task, kind, responsibility, assignment, schema, blocking)
            except WorkforceError as exc:
                self._drop_attempt(task)
                mission.status = "failed"
                mission.record("workforce_error", task=task.task_id, detail=str(exc))
                return
            if ok is None:  # provider outage: redo the whole attempt later
                return
            passed, failed_by = ok, (None if ok else label)
        mission.record("task_attempt", task=task.task_id, attempt=task.attempts, passed=passed)
        if passed:
            task.status = "passed"
        elif self._ask_instead(mission, task):
            return
        elif task.attempts >= MAX_ATTEMPTS:
            self._escalate_task(mission, task, f"Task {task.task_id} failed {failed_by} {task.attempts} times.")

    def _ask_instead(self, mission: Mission, task: Task) -> bool:
        """A reviewer says the task can't be done right without a business decision: ask the founder
        (Home -> Needs you) instead of burning attempts on guesses. At most MAX_QUESTION_ROUNDS."""
        builds = [i for i, h in enumerate(task.handoffs) if h.get("kind") == "build"]
        latest = task.handoffs[builds[-1]:] if builds else task.handoffs  # this attempt's reviews only
        asked = list(dict.fromkeys(str(h["decision_needed"]).strip()[:500] for h in latest
                                   if str(h.get("decision_needed") or "").strip()))
        with self._mission_lock:
            # Questions raised while others are already waiting join the same round (parallel tasks).
            joining = mission.status == "awaiting_decision"
            if not asked or mission.status in ("escalated", "failed") or \
                    (not joining and handoffs.answered_rounds(mission) >= handoffs.MAX_QUESTION_ROUNDS):
                return False
            mission.questions = list(dict.fromkeys(mission.questions + asked))[:8]
            mission.status = "awaiting_decision"
            mission.record("questions_asked", task=task.task_id, questions=asked)
        return True

    @staticmethod
    def _drop_attempt(task: Task) -> None:
        """Forget the current attempt (its handoffs and the count); the work is redone in full."""
        task.handoffs = [h for h in task.handoffs if h.get("attempt") != task.attempts]
        task.attempts -= 1

    @staticmethod
    def _changes(mission: Mission) -> Dict[str, Any]:
        """Client missions: the real change set against the code as received (reviewers and the
        writer must not rely on the builder's own list of changed files)."""
        if not mission.baseline_dir:
            return {"files": [], "diff": "(the baseline is not available for this mission)", "truncated": False}
        from app.platform.clients.work import changes

        return changes(mission.workspace_root, mission.baseline_dir)

    def _extra_review(self, mission: Mission, task: Task, kind: str, responsibility: str, assignment,
                      schema: Dict[str, Any], is_blocker) -> Optional[bool]:
        """A reviewer after QA (UX Designer, Security Reviewer). None means the provider failed."""
        reviewer = self.workforce.for_responsibility(responsibility)
        reviewed = run_employee(reviewer, assignment=assignment(),
                                workspace_root=mission.workspace_root, chat=self._chat_for(mission, reviewer),
                                on_event=self._watch(mission, reviewer, f"reviewing {task.task_id} ({kind.split('_')[0]})"),
                                usage_sink=mission.usage, output_schema=schema, allow_writes=False, allow_execution=False,
                                sandboxed=mission.sandboxed)
        if reviewed.run.status == "provider_error":
            self._drop_attempt(task)
            self._pause(mission, reviewer.employee_id, reviewed.run.error)
            return None
        verdict = reviewed.output or {"verdict": "FAIL", "evidence": f"{reviewer.name} produced no verdict ({reviewed.run.status}).",
                                      "issues": [{"severity": "blocker" if kind == "ux_verdict" else "critical",
                                                  "introduced_by_change": True,
                                                  "detail": f"No {reviewer.name} verdict was recorded."}]}
        issues = verdict.get("issues") or []
        blockers = [i for i in issues if is_blocker(i)]
        # A FAIL that lists only non-blocking issues (e.g. problems already in the client's code) passes;
        # a FAIL with no issues at all stays a FAIL.
        # A reviewer's business question always stops the task, whatever else it lists.
        passed = not blockers and (verdict["verdict"] == "PASS" or bool(issues)) and \
            not str(verdict.get("decision_needed") or "").strip()
        task.handoffs.append({"kind": kind, "attempt": task.attempts, "employee": reviewer.employee_id,
                              **verdict, "verdict": "PASS" if passed else "FAIL"})
        return passed

    def _handover(self, mission: Mission) -> None:
        """Client missions: the Technical Writer explains the finished work in plain English. Never
        blocks delivery: a failure records why and the founder writes the note instead."""
        try:
            writer = self.workforce.for_responsibility("write_handover")
        except WorkforceError as exc:
            mission.handover = {"error": str(exc)}
            mission.record("handover_skipped", reason=str(exc))
            return
        result = run_employee(writer, assignment=handoffs.handover_assignment(mission, self._changes(mission)),
                              workspace_root=mission.workspace_root,
                              chat=self._chat_for(mission, writer), usage_sink=mission.usage,
                              on_event=self._watch(mission, writer, "writing the client handover"),
                              output_schema=handoffs.HANDOVER_SCHEMA, allow_writes=False,
                              allow_execution=False, sandboxed=mission.sandboxed)
        if result.output:
            mission.handover = {**result.output, "employee": writer.employee_id}
            mission.record("handover_written", employee=writer.employee_id)
        else:
            reason = result.run.error or result.run.status
            mission.handover = {"error": f"The Technical Writer couldn't write the handover ({reason})."}
            mission.record("handover_skipped", reason=reason)
