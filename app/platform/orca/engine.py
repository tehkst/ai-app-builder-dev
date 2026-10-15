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
from typing import Any, Dict, List, Optional

from app.platform.nautilus.messages import ChatFn
from app.platform.nautilus.workspace_tools import run_workspace_command
from app.platform.orca import handoffs
from app.platform.orca.employee_runner import run_employee
from app.platform.orca.models import MAX_ATTEMPTS, Mission, Task
from app.platform.orca.store import MissionStore
from app.platform.orca.workforce import Workforce, load_workforce
from app.platform.services.nautilus_repair_service.sandbox import within_approved_base

CHECK_TIMEOUT_SECONDS = 300
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

    def run(self, mission_id: str, max_steps: int = MAX_STEPS_PER_RUN) -> Mission:
        """Advance the mission until it finishes, pauses for the founder, or max_steps is hit."""
        mission = self._load(mission_id)
        for _ in range(max_steps):
            if mission.finished or mission.status == "awaiting_execution_approval":
                break
            self._step(mission)
            self.store.save(mission)
        return mission

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
            self._integrate(mission)

    def _plan(self, mission: Mission) -> None:
        architect = self.workforce.for_responsibility("plan_mission")
        result = run_employee(architect, assignment=handoffs.plan_assignment(mission),
                              workspace_root=mission.workspace_root, chat=self.chat,
                              output_schema=handoffs.PLAN_SCHEMA, allow_writes=False, allow_execution=False)
        planned = (result.output or {}).get("tasks") or []
        if not result.output or not planned or len(planned) > handoffs.MAX_PLANNED_TASKS:
            mission.status = "failed"
            mission.record("planning_failed", employee=architect.employee_id, agent_status=result.run.status,
                           detail=result.run.error or f"Plan had {len(planned)} tasks.")
            return
        mission.plan_summary = result.output["summary"]
        mission.tasks = [Task(f"T{i}", t["title"], t["description"], list(t.get("files") or []),
                              [c for c in t.get("acceptance_checks") or [] if c.strip()])
                         for i, t in enumerate(planned, start=1)]
        has_checks = any(task.acceptance_checks for task in mission.tasks)
        if not has_checks and mission.execution_approval == "pending":
            mission.execution_approval = "not_needed"
        waiting = has_checks and mission.execution_approval == "pending"
        mission.status = "awaiting_execution_approval" if waiting else "building"
        mission.record("planned", employee=architect.employee_id, tasks=len(mission.tasks),
                       awaiting_execution_approval=waiting)

    def _work_task(self, mission: Mission, task: Task) -> None:
        task.attempts += 1
        self.store.save(mission)  # an interrupted attempt still counts toward the limit
        builder = self.workforce.for_responsibility("build_task")
        built = run_employee(builder, assignment=handoffs.build_assignment(mission, task),
                             workspace_root=mission.workspace_root, chat=self.chat,
                             output_schema=handoffs.BUILD_SCHEMA, allow_writes=True,
                             allow_execution=mission.execution_allowed)
        build = built.output or {"summary": f"Builder produced no result ({built.run.status}).", "files_changed": []}
        task.handoffs.append({"kind": "build", "attempt": task.attempts, "employee": builder.employee_id, **build})

        checks = self._run_checks(mission, task.acceptance_checks)
        qa = self.workforce.for_responsibility("review_task")
        reviewed = run_employee(qa, assignment=handoffs.review_assignment(mission, task, build, checks,
                                                                          mission.execution_allowed),
                                workspace_root=mission.workspace_root, chat=self.chat,
                                output_schema=handoffs.VERDICT_SCHEMA, allow_writes=False, allow_execution=False)
        verdict = reviewed.output or {"verdict": "FAIL", "evidence": f"QA produced no verdict ({reviewed.run.status}).",
                                      "issues": [{"severity": "blocker", "detail": "No QA verdict was recorded."}]}
        blockers = [i for i in verdict.get("issues") or [] if i.get("severity") == "blocker"]
        passed = (verdict["verdict"] == "PASS" and not blockers and built.output is not None
                  and all(c["passed"] for c in checks))
        task.handoffs.append({"kind": "qa_verdict", "attempt": task.attempts, "employee": qa.employee_id,
                              **verdict, "verdict": "PASS" if passed else "FAIL", "check_results": checks})
        mission.record("task_attempt", task=task.task_id, attempt=task.attempts, passed=passed)
        if passed:
            task.status = "passed"
        elif task.attempts >= MAX_ATTEMPTS:
            task.status = "escalated"
            mission.status = "escalated"
            mission.escalation = {"reason": f"Task {task.task_id} failed QA {task.attempts} times.",
                                  "task": task.task_id, "attempts": task.handoffs}
            mission.record("escalated", task=task.task_id)

    def _run_checks(self, mission: Mission, commands: List[str]) -> List[Dict[str, Any]]:
        if not mission.execution_allowed:
            return []
        results = []
        for command in commands:
            outcome = run_workspace_command(mission.workspace_root, command, CHECK_TIMEOUT_SECONDS)
            results.append({"command": command, "passed": outcome["exit_code"] == 0,
                            "exit_code": outcome["exit_code"], "output": outcome["output"][-handoffs.CHECK_OUTPUT_CHARS:]})
        return results

    def _integrate(self, mission: Mission) -> None:
        if not mission.execution_allowed:
            mission.status = "complete_unverified"
            mission.record("completed", verified=False, reason=f"execution {mission.execution_approval}")
            return
        results = self._run_checks(mission, [c for t in mission.tasks for c in t.acceptance_checks])
        mission.integration = {"check_results": results, "passed": all(r["passed"] for r in results)}
        if mission.integration["passed"]:
            mission.status = "complete"
            mission.record("completed", verified=True, checks=len(results))
        else:
            mission.status = "escalated"
            mission.escalation = {"reason": "Integration gate failed: a previously passing check now fails.",
                                  "check_results": results}
            mission.record("escalated", stage="integration")
