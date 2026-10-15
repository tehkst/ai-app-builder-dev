"""Orca: the orchestrator that runs missions with AI employees.

Orca itself is deterministic code (so the process is predictable and auditable); the employees
do the thinking on Nautilus. Pipeline (adapted from NEXUS): the architect plans; each task goes
through a Dev↔QA loop (builder, acceptance checks, QA verdict; FAIL returns to the builder with
the findings; MAX_ATTEMPTS then escalate); an integration gate re-runs every check. State is
saved after every step, so a mission resumes after a restart.

Executing generated code (acceptance checks, builder commands) requires the founder's approval
for the mission; without it, Orca still plans, builds and reviews, but finishes
`complete_unverified`.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from app.platform.nautilus.messages import ChatFn
from app.platform.orca import gates, handoffs
from app.platform.orca.employee_runner import run_employee
from app.platform.orca.models import MAX_ATTEMPTS, Mission, Task
from app.platform.orca.store import MissionStore
from app.platform.orca.workforce import Workforce, load_workforce
from app.platform.services.nautilus_repair_service.sandbox import within_approved_base

MAX_STEPS_PER_RUN = 200


class Orca:
    def __init__(self, *, chat: Optional[ChatFn] = None, workforce: Optional[Workforce] = None,
                 store: Optional[MissionStore] = None, sandbox_base: Optional[Path] = None) -> None:
        self._chat = chat
        self.workforce = workforce or load_workforce()
        self.store = store or MissionStore()
        self.sandbox_base = sandbox_base

    @property
    def chat(self) -> ChatFn:
        if self._chat is None:
            from app.platform.nautilus.chat_providers import build_chat_fn
            from app.platform.persistence.database import create_platform_tables

            create_platform_tables()  # provider selection reads the runtime settings table
            self._chat = build_chat_fn()
        return self._chat

    # ---- founder-facing operations -----------------------------------------------------

    def start_mission(self, goal: str, workspace_root: str, *, execution_approved: bool = False) -> Mission:
        workspace = Path(workspace_root).resolve()
        if not goal.strip():
            raise ValueError("A mission needs a goal.")
        if not workspace.is_dir() or not within_approved_base(workspace, self.sandbox_base):
            raise ValueError("Mission workspace must be an existing directory inside the approved sandbox base.")
        mission = Mission("ORCA-" + uuid.uuid4().hex[:12].upper(), goal.strip(), str(workspace),
                          execution_approval="approved" if execution_approved else "pending")
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

    def retry_task(self, mission_id: str, *, decided_by: str = "founder") -> Mission:
        """Founder override: give an escalated task a fresh set of Dev↔QA attempts."""
        mission = self._load(mission_id)
        task = next((t for t in mission.tasks if t.status == "escalated"), None)
        if mission.status != "escalated" or task is None:
            raise ValueError("Only a mission escalated on a task can be retried.")
        task.status, task.attempts = "pending", 0
        mission.status, mission.escalation = "building", None
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
        for _ in range(max_steps):
            if mission.finished or mission.status in ("awaiting_execution_approval", "paused"):
                break
            self._step(mission)
            self.store.save(mission)
        return mission

    def _pause(self, mission: Mission, employee: str, error: Optional[str]) -> None:
        """The AI provider failed (missing key, outage, timeout): that's not the employee's
        fault, so pause instead of failing or using up an attempt."""
        mission.resume_status, mission.status = mission.status, "paused"
        mission.paused_reason = f"AI provider error while {employee} was working: {error or 'unknown error'}"
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
            task = next((t for t in mission.tasks if t.status == "pending"), None)
            if task is None:
                mission.status = "integration"
            else:
                self._work_task(mission, task)
        elif mission.status == "integration":
            gates.integrate(mission)

    def _plan(self, mission: Mission) -> None:
        """The architect plans; a plan with problems gets one corrective round, then fails."""
        architect = self.workforce.for_responsibility("plan_mission")
        assignment, problems = handoffs.plan_assignment(mission), []
        for _ in range(2):
            result = run_employee(architect, assignment=assignment, workspace_root=mission.workspace_root,
                                  chat=self.chat, output_schema=handoffs.PLAN_SCHEMA,
                                  allow_writes=False, allow_execution=False)
            if result.run.status == "provider_error":
                self._pause(mission, architect.employee_id, result.run.error)
                return
            planned = (result.output or {}).get("tasks") or []
            problems = handoffs.plan_problems(planned, mission.workspace_root) if result.output else \
                [f"no plan was submitted ({result.run.status}{': ' + result.run.error if result.run.error else ''})"]
            if not problems:
                break
            assignment = handoffs.plan_assignment(mission) + "\n\n## Your previous plan was rejected\n" + \
                "\n".join(f"- {p}" for p in problems) + "\nFix these and submit the whole plan again."
        if problems:
            mission.status = "failed"
            mission.record("planning_failed", employee=architect.employee_id, problems=problems)
            return
        mission.plan_summary = result.output["summary"]
        mission.tasks = [Task(f"T{i}", t["title"], t["description"], list(t.get("files") or []),
                              [c for c in t["acceptance_checks"] if c.strip()],
                              specialty=t.get("specialty") or "general")
                         for i, t in enumerate(planned, start=1)]
        waiting = mission.execution_approval == "pending"  # every task has checks to run
        mission.status = "awaiting_execution_approval" if waiting else "building"
        mission.record("planned", employee=architect.employee_id, tasks=len(mission.tasks),
                       awaiting_execution_approval=waiting)

    def _escalate_task(self, mission: Mission, task: Task, reason: str) -> None:
        task.status, mission.status = "escalated", "escalated"
        mission.escalation = {"reason": reason, "task": task.task_id, "attempts": task.handoffs}
        mission.record("escalated", task=task.task_id)

    def _work_task(self, mission: Mission, task: Task) -> None:
        if task.attempts >= MAX_ATTEMPTS:  # e.g. the process stopped during the last attempt
            self._escalate_task(mission, task, f"Task {task.task_id} used all {MAX_ATTEMPTS} attempts "
                                               "(the last one was interrupted).")
            return
        task.attempts += 1
        self.store.save(mission)  # an interrupted attempt still counts toward the limit
        builder = self.workforce.find(f"build_task:{task.specialty}") or self.workforce.for_responsibility("build_task")
        built = run_employee(builder, assignment=handoffs.build_assignment(mission, task),
                             workspace_root=mission.workspace_root, chat=self.chat,
                             output_schema=handoffs.BUILD_SCHEMA, allow_writes=True,
                             allow_execution=mission.execution_allowed)
        if built.run.status == "provider_error":
            task.attempts -= 1
            self._pause(mission, builder.employee_id, built.run.error)
            return
        build = built.output or {"summary": f"Builder produced no result ({built.run.status}).", "files_changed": []}
        task.handoffs.append({"kind": "build", "attempt": task.attempts, "employee": builder.employee_id, **build})

        checks = gates.run_checks(mission, task.acceptance_checks)
        qa = self.workforce.for_responsibility("review_task")
        reviewed = run_employee(qa, assignment=handoffs.review_assignment(mission, task, build, checks,
                                                                          mission.execution_allowed),
                                workspace_root=mission.workspace_root, chat=self.chat,
                                output_schema=handoffs.VERDICT_SCHEMA, allow_writes=False, allow_execution=False)
        if reviewed.run.status == "provider_error":
            task.handoffs.pop()  # the build stays in the workspace; the attempt is redone in full
            task.attempts -= 1
            self._pause(mission, qa.employee_id, reviewed.run.error)
            return
        verdict = reviewed.output or {"verdict": "FAIL", "evidence": f"QA produced no verdict ({reviewed.run.status}).",
                                      "issues": [{"severity": "blocker", "detail": "No QA verdict was recorded."}]}
        blockers = [i for i in verdict.get("issues") or [] if i.get("severity") == "blocker"]
        passed = (verdict["verdict"] == "PASS" and not blockers and built.output is not None
                  and all(c["passed"] for c in checks))
        task.handoffs.append({"kind": "qa_verdict", "attempt": task.attempts, "employee": qa.employee_id,
                              **verdict, "verdict": "PASS" if passed else "FAIL", "check_results": checks})
        failed_by = None if passed else "QA"
        if passed and task.specialty == "frontend" and self.workforce.find("review_ux"):
            ux_passed = self._ux_review(mission, task, build, verdict)
            if ux_passed is None:  # provider outage: redo the whole attempt later
                return
            passed, failed_by = ux_passed, (None if ux_passed else "UX review")
        mission.record("task_attempt", task=task.task_id, attempt=task.attempts, passed=passed)
        if passed:
            task.status = "passed"
        elif task.attempts >= MAX_ATTEMPTS:
            self._escalate_task(mission, task, f"Task {task.task_id} failed {failed_by} {task.attempts} times.")

    def _ux_review(self, mission: Mission, task: Task, build: dict, qa_verdict: dict) -> Optional[bool]:
        """User-facing tasks also need the UX Designer's PASS. None means the provider failed."""
        designer = self.workforce.for_responsibility("review_ux")
        reviewed = run_employee(designer, assignment=handoffs.ux_review_assignment(mission, task, build, qa_verdict),
                                workspace_root=mission.workspace_root, chat=self.chat,
                                output_schema=handoffs.VERDICT_SCHEMA, allow_writes=False, allow_execution=False)
        if reviewed.run.status == "provider_error":
            del task.handoffs[-2:]  # drop this attempt's build + QA verdict; it is redone in full
            task.attempts -= 1
            self._pause(mission, designer.employee_id, reviewed.run.error)
            return None
        verdict = reviewed.output or {"verdict": "FAIL", "evidence": f"UX produced no verdict ({reviewed.run.status}).",
                                      "issues": [{"severity": "blocker", "detail": "No UX verdict was recorded."}]}
        blockers = [i for i in verdict.get("issues") or [] if i.get("severity") == "blocker"]
        passed = verdict["verdict"] == "PASS" and not blockers
        task.handoffs.append({"kind": "ux_verdict", "attempt": task.attempts, "employee": designer.employee_id,
                              **verdict, "verdict": "PASS" if passed else "FAIL"})
        return passed
