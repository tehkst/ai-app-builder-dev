"""Check for acceptance checks the sandbox can't run (found in the pilot: `npm test` also ran
integration tests that need Postgres, so a correct nodemailer upgrade failed QA three times and
escalated). Such a check is marked "couldn't run here": it doesn't fail the task, the mission
finishes unverified with it named, and the handover tells the client to run it. The architect is
told to pick offline checks and sees the project's scripts; a retry can replace a task's checks.
Fake sandbox, scripted employees, no Docker."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

from app.platform.container_sandbox import service as sandbox
from app.platform.orca import MissionStore, Orca, gates, sandbox_commands
from app.platform.orca.handoffs import runner_note
from app.platform.orca.lockfile_check import HANDOVER, client_mission
from app.platform.orca.orca_check import PASS, Pod, finish, write

DB_ERROR = "Error: TEST_DATABASE_OWNER_URL and TEST_DATABASE_URL must be set (see .env.example)"
PLAN = {"summary": "Upgrade left-pad.", "tasks": [
    {"title": "Upgrade left-pad", "description": "Bump left-pad to 1.3.0 in package.json.", "specialty": "upgrade",
     "files": ["package.json"], "acceptance_checks": ["npm test", "npm run lint"]}]}
BUMPED = json.dumps({"name": "shop", "dependencies": {"left-pad": "1.3.0"}})


class FakeSandbox:
    """Installs succeed; `npm test` fails as a suite with database tests does; other commands pass
    unless listed in `failing`."""

    def __init__(self, failing: Dict[str, str] = None) -> None:
        self.commands: List[List[str]] = []
        self.failing = failing or {}

    def __call__(self, source_dir, command, image, **options) -> sandbox.SandboxResult:
        self.commands.append(list(command))
        base = dict(command=list(command), image=image, timed_out=False, duration_seconds=0.1,
                    network=options.get("network_reason") is not None)
        if options.get("keep_workdir"):
            scratch = Path(tempfile.mkdtemp(prefix="fake-offline-")) / "work"
            (scratch / "node_modules").mkdir(parents=True)
            return sandbox.SandboxResult(exit_code=0, stdout="Done", stderr="", workdir=str(scratch), **base)
        text = " ".join(command)
        if text == "npm test":
            return sandbox.SandboxResult(exit_code=1, stdout="No test files found, exiting with code 1", stderr=DB_ERROR, **base)
        if text in self.failing:
            return sandbox.SandboxResult(exit_code=1, stdout=self.failing[text], stderr="", **base)
        return sandbox.SandboxResult(exit_code=0, stdout="ok", stderr="", **base)


def approved_run(orca: Orca, mission_id: str, fake: FakeSandbox):
    with mock.patch.object(sandbox_commands, "run_in_sandbox", fake), \
            mock.patch.object(gates, "run_workspace_command", lambda *a, **k: (_ for _ in ()).throw(AssertionError("host"))):
        orca.run(mission_id)
        orca.decide_execution(mission_id, approved=True)
        return orca.run(mission_id)


def check_signs() -> None:
    needs = sandbox_commands.needs_outside_service
    assert "database" in needs(DB_ERROR)
    assert "database" in needs("connect ECONNREFUSED 127.0.0.1:5432")
    assert "database" in needs("PrismaClientInitializationError: Can't reach database server at `db:5432`")
    assert "internet" in needs("getaddrinfo ENOTFOUND api.stripe.com")
    for real in ("AssertionError: expected 2 to be 3", "DATABASE_URL looks fine", "ECONNREFUSED 127.0.0.1:3000", ""):
        assert needs(real) is None, real


def check_database_tests_dont_fail_the_task(base: Path, store: MissionStore) -> None:
    pod = Pod({"Software Architect": [*finish("p1", PLAN)],
               "Upgrade Specialist": [*write("b1", "package.json", BUMPED, "bumped left-pad")],
               "QA Lead": [*finish("q1", PASS)], "Security Reviewer": [*finish("s1", PASS)],
               "Technical Writer": [*finish("w1", HANDOVER)]})
    orca, mission, _ = client_mission(base, "CL-db", pod, store)
    mission = approved_run(orca, mission.mission_id, FakeSandbox())
    assert mission.status == "complete_unverified", (mission.status, mission.escalation)
    task = mission.tasks[0]
    assert task.status == "passed" and task.attempts == 1, (task.status, task.attempts)
    assert mission.integration["not_run"] == [{"command": "npm test", "needs": sandbox_commands.SERVICE_SIGNS[0][1]}]
    assert any(e["event"] == "completed" and e.get("not_run") == ["npm test"] for e in mission.events)
    qa_brief = pod.briefings["QA Lead"][0]
    assert "`npm test` -> NOT RUN (needs a database" in qa_brief and "don't fail the task" in qa_brief, qa_brief
    handover = pod.briefings["Technical Writer"][0]
    assert "could NOT run" in handover and "- `npm run lint`" in handover and "npm test` (needs" in handover, handover

    from app.platform.orca.engine import STATUS_LINES
    assert STATUS_LINES["complete_unverified"] == "done, but not everything could be checked"


def check_only_unrunnable_checks_fail(base: Path, store: MissionStore) -> None:
    """Nothing really ran: the task isn't verified, so it doesn't pass."""
    only = {"summary": "s", "tasks": [{**PLAN["tasks"][0], "acceptance_checks": ["npm test"]}]}
    pod = Pod({"Software Architect": [*finish("p1", only)],
               "Upgrade Specialist": [*write("b1", "package.json", BUMPED, "bumped")], "QA Lead": [*finish("q1", PASS)]})
    orca, mission, _ = client_mission(base, "CL-only", pod, store)
    with mock.patch.object(sandbox_commands, "run_in_sandbox", FakeSandbox()):
        orca.run(mission.mission_id)
        orca.decide_execution(mission.mission_id, approved=True)
        orca.run(mission.mission_id, max_steps=2)  # install, then the first attempt
    task = store.load(mission.mission_id).tasks[0]
    assert task.status != "passed" and task.handoffs[-1]["verdict"] == "FAIL", task.handoffs[-1]
    assert not gates.checks_ok([{"passed": False, "not_run": "x"}]) and gates.checks_ok([])


def check_real_failures_still_fail(base: Path, store: MissionStore) -> None:
    """A real failure next to an unrunnable check still fails the task; host missions never mark not_run."""
    pod = Pod({"Software Architect": [*finish("p1", PLAN)],
               "Upgrade Specialist": [*write("b1", "package.json", BUMPED, "bumped")], "QA Lead": [*finish("q1", PASS)]})
    orca, mission, _ = client_mission(base, "CL-real", pod, store)
    with mock.patch.object(sandbox_commands, "run_in_sandbox", FakeSandbox({"npm run lint": "1 error"})):
        orca.run(mission.mission_id)
        orca.decide_execution(mission.mission_id, approved=True)
        orca.run(mission.mission_id, max_steps=2)
    verdict = store.load(mission.mission_id).tasks[0].handoffs[-1]
    assert verdict["verdict"] == "FAIL", verdict

    class Host:
        sandboxed, execution_allowed, workspace_root = False, True, str(base)

    with mock.patch.object(gates, "run_workspace_command", lambda *a, **k: {"exit_code": 1, "output": DB_ERROR}):
        result = gates.run_checks(Host(), ["npm test"])  # type: ignore[arg-type]
    assert "not_run" not in result[0], result


def check_retry_replaces_checks(base: Path, store: MissionStore) -> None:
    pod = Pod({"Software Architect": [*finish("p1", PLAN)]})
    orca, mission, _ = client_mission(base, "CL-retry", pod, store)
    orca.run(mission.mission_id)
    mission = store.load(mission.mission_id)
    mission.status, mission.tasks[0].status, mission.tasks[0].attempts = "escalated", "escalated", 3
    store.save(mission)
    try:
        orca.retry_task(mission.mission_id, acceptance_checks=["curl https://example.com"])
        raise AssertionError("a disallowed check was accepted")
    except ValueError as exc:
        assert "not allowed" in str(exc), exc
    assert store.load(mission.mission_id).status == "escalated", "a refused retry changes nothing"
    retried = orca.retry_task(mission.mission_id, acceptance_checks=["npm run test:unit", " ", "npm run typecheck"])
    assert retried.tasks[0].acceptance_checks == ["npm run test:unit", "npm run typecheck"]
    assert retried.tasks[0].status == "pending" and retried.status == "building"
    event = next(e for e in retried.events if e["event"] == "checks_replaced")
    assert event["old"] == ["npm test", "npm run lint"], event


def check_planner_brief(base: Path) -> None:
    workspace = base / "brief"
    workspace.mkdir()
    (workspace / "package.json").write_text(json.dumps({"scripts": {"test": "vitest run", "test:unit": "vitest run --project unit",
                                                                    "typecheck": "tsc --noEmit"}}))

    class Sandboxed:
        sandboxed, workspace_root = True, str(workspace)

    note = runner_note(Sandboxed())  # type: ignore[arg-type]
    assert "no database" in note and "npm run test:unit" in note and "Every task except docs" in note, note
    assert "- test:unit: vitest run --project unit" in note and "- typecheck: tsc --noEmit" in note, note
    (workspace / "package.json").write_text("not json")
    assert "scripts (run as" not in runner_note(Sandboxed())  # type: ignore[arg-type]


def check_code_tasks_need_real_checks(base: Path) -> None:
    """Found in the pilot: two upgrade tasks were accepted on lint alone."""
    from app.platform.orca.handoffs import plan_problems

    workspace = base / "real-checks"
    workspace.mkdir()
    (workspace / "package.json").write_text(json.dumps({"scripts": {"lint": "eslint", "test:unit": "vitest run", "typecheck": "tsc"}}))
    lint_only = [{"title": "Bump zod", "specialty": "upgrade", "acceptance_checks": ["grep -q zod package.json", "npm run lint"]}]
    problems = plan_problems(lint_only, str(workspace), sandboxed=True)
    assert len(problems) == 1 and "`npm run test:unit`, `npm run typecheck`" in problems[0], problems
    assert plan_problems(lint_only, str(workspace)) == [], "missions on this machine keep their own rules"
    docs = [{"title": "Update README", "specialty": "docs", "acceptance_checks": ["grep -q Setup README.md"]}]
    assert plan_problems(docs, str(workspace), sandboxed=True) == [], "docs tasks don't run code"
    for good in ("npm run typecheck", "npm run test:unit", "npm test", "npm run build"):
        assert plan_problems([dict(lint_only[0], acceptance_checks=["npm run lint", good])], str(workspace), sandboxed=True) == [], good
    bare = base / "no-scripts"
    bare.mkdir()
    (bare / "package.json").write_text(json.dumps({"scripts": {"lint": "eslint"}}))
    assert plan_problems(lint_only, str(bare), sandboxed=True) == [], "a project with nothing to run isn't blocked"
    assert not sandbox_commands.runs_project_code("npm run lint") and not sandbox_commands.runs_project_code("grep -q x y")
    assert sandbox_commands.runs_project_code("python -m pytest -q") and sandbox_commands.runs_project_code("vendor/bin/phpunit")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        store = MissionStore(base / "missions")
        check_signs()
        check_planner_brief(base)
        check_code_tasks_need_real_checks(base)
        check_database_tests_dont_fail_the_task(base, store)
        check_only_unrunnable_checks_fail(base, store)
        check_real_failures_still_fail(base, store)
        check_retry_replaces_checks(base, store)
    print("OFFLINE CHECKS CHECK PASSED")


if __name__ == "__main__":
    main()
