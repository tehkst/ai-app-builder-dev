"""Deterministic check for Orca (no network): a scripted pod plays the architect, builder and QA
lead, recognised by their role prompts, through full missions."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, List

from app.platform.nautilus.loop_check import call, turn
from app.platform.nautilus.messages import ChatTurn, ToolCall
from app.platform.orca import MissionStore, Orca, load_workforce
from app.platform.orca.employee_runner import permissions_for

CHECK_T1 = "python3 -c \"import greet; assert greet.greet() == 'hello'\""
CHECK_T2 = "grep -q Greet README.md"
PLAN = {"summary": "Add a greet module, then document it.", "tasks": [
    {"title": "Add greet()", "description": "Create greet.py with greet() returning 'hello'.",
     "files": ["greet.py"], "acceptance_checks": [CHECK_T1]},
    {"title": "Document greet", "description": "Create README.md mentioning Greet.",
     "files": ["README.md"], "acceptance_checks": [CHECK_T2]},
]}
PASS = {"verdict": "PASS", "evidence": "Read the file; matches the task.", "issues": []}
FAIL = {"verdict": "FAIL", "evidence": "Wrong output.", "issues": [{"severity": "blocker", "detail": "returns hi"}]}


def finish(call_id: str, output: Dict) -> List[ChatTurn]:
    return [turn("", [call(call_id, "final_output", **output)]), turn("Done.")]


def write(call_id: str, path: str, content: str, summary: str) -> List[ChatTurn]:
    return [turn("", [call(call_id, "write_file", path=path, content=content)]),
            *finish(call_id + "f", {"summary": summary, "files_changed": [path]})]


class Pod:
    """Scripted model for all employees; records every briefing each role receives."""

    def __init__(self, scripts: Dict[str, List[ChatTurn]]) -> None:
        self.scripts = scripts
        self.briefings: Dict[str, List[str]] = {role: [] for role in scripts}

    def __call__(self, messages, tools) -> ChatTurn:
        role = next(r for r in self.scripts if messages[0]["content"].startswith("# " + r))
        if len(messages) == 2:
            self.briefings[role].append(messages[1]["content"])
        item = self.scripts[role].pop(0) if self.scripts[role] else turn("Done.")
        if isinstance(item, Exception):  # simulated provider outage
            raise item
        return item


def new_workspace(base: Path, name: str) -> Path:
    workspace = base / name
    workspace.mkdir()
    (workspace / "app.txt").write_text("existing project\n")
    return workspace


def check_full_mission_with_retry(base: Path, store: MissionStore) -> None:
    pod = Pod({
        "Software Architect": [turn("", [call("l1", "list_files")]), *finish("p1", PLAN)],
        "Builder": [*write("b1", "greet.py", "def greet():\n    return 'hi'\n", "first try"),
                    *write("b2", "greet.py", "def greet():\n    return 'hello'\n", "fixed return value"),
                    *write("b3", "README.md", "# Greet\n", "docs")],
        "QA Lead": [*finish("q1", PASS), *finish("q2", PASS), *finish("q3", PASS)],
    })
    orca = Orca(chat=pod, store=store, sandbox_base=base)
    mission = orca.start_mission("Add a greeting feature", str(new_workspace(base, "happy")))
    mission = orca.run(mission.mission_id)
    assert mission.status == "awaiting_execution_approval" and len(mission.tasks) == 2, mission.status

    restarted = Orca(chat=pod, store=MissionStore(store.directory), sandbox_base=base)  # survives restart
    restarted.decide_execution(mission.mission_id, approved=True)
    mission = restarted.run(mission.mission_id)
    t1, t2 = mission.tasks
    assert mission.status == "complete" and mission.integration["passed"], (mission.status, mission.escalation)
    assert (t1.status, t1.attempts, t2.status, t2.attempts) == ("passed", 2, "passed", 1), (t1, t2)
    first_verdict = [h for h in t1.handoffs if h["kind"] == "qa_verdict"][0]
    assert first_verdict["verdict"] == "FAIL", "a failing check must override QA's PASS"
    retry_briefing = pod.briefings["Builder"][1]
    assert "verdict on your previous attempt: FAIL" in retry_briefing and "Failed check" in retry_briefing
    assert "Code execution IS approved" not in pod.briefings["QA Lead"][0]  # QA never executes
    assert "T2 (pending): Document greet" in pod.briefings["QA Lead"][0], "QA must see other tasks' scope"
    assert "T1 (passed): Add greet()" in pod.briefings["Builder"][2], "builder must see other tasks' scope"
    assert store.load(mission.mission_id).status == "complete"
    assert [e["event"] for e in mission.events][-1] == "completed"


def check_escalation(base: Path, store: MissionStore) -> None:
    one_task = {"summary": "s", "tasks": [PLAN["tasks"][0]]}
    pod = Pod({"Software Architect": finish("p", one_task),
               "Builder": [t for i in range(3) for t in write(f"b{i}", "greet.py", "x = 1\n", "attempt")],
               "QA Lead": [t for i in range(3) for t in finish(f"q{i}", FAIL)]})
    orca = Orca(chat=pod, store=store, sandbox_base=base)
    mission = orca.start_mission("Add greet", str(new_workspace(base, "escalate")), execution_approved=True)
    mission = orca.run(mission.mission_id)
    assert mission.status == "escalated" and mission.tasks[0].attempts == 3, mission.status
    assert len([h for h in mission.escalation["attempts"] if h["kind"] == "qa_verdict"]) == 3


def check_provider_outage_pauses_and_retry(base: Path, store: MissionStore) -> None:
    one_task = {"summary": "s", "tasks": [PLAN["tasks"][0]]}
    outage = RuntimeError("DEEPSEEK_API_KEY is not configured")
    pod = Pod({"Software Architect": [outage, *finish("p", one_task)],
               # after the QA outage the whole attempt is redone, so the builder works twice
               "Builder": [outage, *write("b1", "greet.py", "def greet():\n    return 'hello'\n", "done"),
                           *write("b2", "greet.py", "def greet():\n    return 'hello'\n", "redone")],
               "QA Lead": [outage, *finish("q1", PASS)]})
    orca = Orca(chat=pod, store=store, sandbox_base=base)
    mission = orca.start_mission("Add greet", str(new_workspace(base, "outage")), execution_approved=True)
    expected = [("architect", "planning"), ("builder", "building"), ("qa_lead", "building")]
    for employee, resume_status in expected:  # each outage pauses without failing or using an attempt
        mission = orca.run(mission.mission_id)
        assert mission.status == "paused" and employee in mission.paused_reason, (mission.status, mission.paused_reason)
        assert mission.resume_status == resume_status and "DEEPSEEK_API_KEY" in mission.paused_reason
        assert all(t.attempts == 0 for t in mission.tasks), [t.attempts for t in mission.tasks]
    mission = orca.run(mission.mission_id)
    assert mission.status == "complete" and mission.tasks[0].attempts == 1, (mission.status, mission.tasks[0])
    assert [h["kind"] for h in mission.tasks[0].handoffs] == ["build", "qa_verdict"], mission.tasks[0].handoffs

    escalated = next(store.load(i) for i in store.list_ids() if store.load(i).status == "escalated")
    orca._chat = Pod({"Builder": write("r", "greet.py", "def greet():\n    return 'hello'\n", "fixed"),
                      "QA Lead": finish("rq", PASS)})
    retried = orca.retry_task(escalated.mission_id)
    assert retried.status == "building" and retried.tasks[0].attempts == 0, retried.status
    mission = orca.run(escalated.mission_id)
    assert mission.status == "complete" and len(mission.tasks[0].handoffs) == 8, mission.status
    for bad in (mission.mission_id,):
        try:
            orca.retry_task(bad)
            raise AssertionError("a completed mission cannot be retried")
        except ValueError:
            pass


def check_declined_execution(base: Path, store: MissionStore) -> None:
    plan = {"summary": "s", "tasks": [{"title": "t", "description": "d", "acceptance_checks": ["touch ran.txt"]}]}
    pod = Pod({"Software Architect": finish("p", plan),
               "Builder": [turn("", [call("x", "run_command", command="python3 -c 'print(1)'")]),
                           *write("b", "a.txt", "a\n", "wrote a")],
               "QA Lead": finish("q", PASS)})
    orca = Orca(chat=pod, store=store, sandbox_base=base)
    workspace = new_workspace(base, "declined")
    mission = orca.run(orca.start_mission("Do t", str(workspace)).mission_id)
    orca.decide_execution(mission.mission_id, approved=False)
    mission = orca.run(mission.mission_id)
    assert mission.status == "complete_unverified", mission.status
    assert not (workspace / "ran.txt").exists(), "checks must not run without execution approval"
    assert "not approved" in pod.briefings["QA Lead"][0]


def check_guard_rails(base: Path, store: MissionStore, outside: Path) -> None:
    orca = Orca(chat=Pod({"Software Architect": [turn("I have no plan.")]}), store=store, sandbox_base=base)
    for bad in (outside, base / "missing"):
        try:
            orca.start_mission("goal", str(bad))
            raise AssertionError(f"workspace {bad} should be rejected")
        except ValueError:
            pass
    failed = orca.run(orca.start_mission("goal", str(new_workspace(base, "noplan"))).mission_id)
    assert failed.status == "failed", failed.status
    workforce = load_workforce()
    builder, qa = workforce.get("builder"), workforce.get("qa_lead")
    command = ToolCall("c", "run_command", {"command": "python3 x.py"})
    write_call = ToolCall("w", "write_file", {"path": "a", "content": ""})
    assert not permissions_for(builder, allow_writes=True, allow_execution=False).approver(command)
    assert permissions_for(builder, allow_writes=True, allow_execution=True).approver(command)
    assert not permissions_for(qa, allow_writes=False, allow_execution=False).approver(write_call)


def main() -> None:
    with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
        base = Path(root, "sandboxes")
        base.mkdir()
        store = MissionStore(Path(root, "missions"))
        check_full_mission_with_retry(base, store)
        check_escalation(base, store)
        check_provider_outage_pauses_and_retry(base, store)
        check_declined_execution(base, store)
        check_guard_rails(base, store, Path(outside))
        assert len(store.list_ids()) == 5, store.list_ids()
    print("ORCA CHECK PASSED")


if __name__ == "__main__":
    main()
