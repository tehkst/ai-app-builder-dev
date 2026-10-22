"""Check for step 5c, parallel tasks: independent tasks with separate files are built side by side
(proved with a barrier both builders must reach together), a builder can't write the other task's
files, dependent tasks wait, overlapping or undeclared files fall back to one at a time, an AI outage
in one parallel task pauses the mission once and a resumed run finishes, and plans with bad
depends_on are rejected."""
from __future__ import annotations

import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Tuple

from app.platform.nautilus.loop_check import call, turn
from app.platform.orca import MissionStore, Orca, Task
from app.platform.orca.handoffs import plan_problems
from app.platform.orca.orca_check import PASS, finish

PLAN = {"summary": "Two independent parts, then one that needs both.", "tasks": [
    {"title": "Part A", "description": "Write a.txt.", "specialty": "general", "files": ["a.txt"],
     "acceptance_checks": ["grep -q A a.txt"], "depends_on": []},
    {"title": "Part B", "description": "Write b.php.", "specialty": "php", "files": ["b.php"],
     "acceptance_checks": ["grep -q B b.php"], "depends_on": []},
    {"title": "Join", "description": "Write c.txt using A and B.", "specialty": "general", "files": ["c.txt"],
     "acceptance_checks": ["grep -q C c.txt"], "depends_on": [1, 2]},
]}


class ThreadedPod:
    """Scripted employees that may be called from several threads: scripts are keyed by role and by
    the task in the briefing, so two conversations never take each other's turns."""

    def __init__(self, scripts: Dict[Tuple[str, str], list]) -> None:
        self.scripts = scripts
        self.lock = threading.Lock()
        self.order: List[str] = []

    def __call__(self, messages, tools):
        system, briefing = messages[0]["content"], messages[1]["content"]
        role = next(r for r, _ in self.scripts if system.startswith("# " + r))
        task = next((t for r, t in self.scripts if r == role and t and f"## Task: {t}\n" in briefing), "")
        with self.lock:
            queue = self.scripts[(role, task)]
            item = queue.pop(0) if queue else turn("Done.")
            if len(messages) == 2:
                self.order.append(f"{role}:{task}")
        if callable(item):
            item = item()
        if isinstance(item, Exception):
            raise item
        return item


def write_turns(cid: str, path: str, content: str, *, meet: threading.Barrier = None, extra: list = ()) -> list:
    def first():
        if meet is not None:
            meet.wait(timeout=20)  # both builders must be here at the same time: proof of parallel work
        return turn("", [*extra, call(cid, "write_file", path=path, content=content)])
    return [first, *finish(cid + "f", {"summary": f"wrote {path}", "files_changed": [path]})]


def check_side_by_side(base: Path) -> None:
    workspace = base / "apps" / "shop"
    workspace.mkdir(parents=True)
    meet = threading.Barrier(2)
    steal = call("steal", "write_file", path="a.txt", content="B was here\n")  # Part B tries Part A's file
    pod = ThreadedPod({
        ("Software Architect", ""): [*finish("p", PLAN)],
        ("Builder", "Part A"): write_turns("a", "a.txt", "A\n", meet=meet),
        ("PHP/WordPress Developer", "Part B"): [*write_turns("b", "b.php", "<?php // B\n", meet=meet, extra=[steal]),
                                                *write_turns("b2", "b.php", "<?php // B again\n")],
        ("Builder", "Join"): write_turns("c", "c.txt", "C\n"),
        ("QA Lead", "Part A"): [*finish("qa", PASS)],
        ("QA Lead", "Part B"): [RuntimeError("provider down"), *finish("qb", PASS)],
        ("QA Lead", "Join"): [*finish("qc", PASS)],
    })
    orca = Orca(chat=pod, store=MissionStore(base / "missions"), sandbox_base=base / "apps")
    mission = orca.start_mission("Build the shop parts", str(workspace))
    orca.run(mission.mission_id)
    assert [t.depends_on for t in orca._load(mission.mission_id).tasks] == [[], [], ["T1", "T2"]]
    orca.decide_execution(mission.mission_id, approved=True)
    mission = orca.run(mission.mission_id)

    # Part A passed; Part B's QA hit an outage, so the mission paused once (Part B's attempt is redone).
    assert mission.status == "paused" and "qa_lead" in (mission.paused_reason or ""), (mission.status, mission.paused_reason)
    t1, t2, t3 = mission.tasks
    assert (t1.status, t2.status, t3.status) == ("passed", "pending", "pending"), (t1.status, t2.status, t3.status)
    assert any(e["event"] == "parallel_batch" and e["tasks"] == ["T1", "T2"] for e in mission.events)
    assert (workspace / "a.txt").read_text() == "A\n", "Part B could not write Part A's file"
    assert sum(1 for e in mission.events if e["event"] == "paused") == 1 and mission.resume_status == "building"

    mission = orca.run(mission.mission_id)  # resume: Part B redone, then Join (which needed both)
    assert mission.status == "complete", (mission.status, mission.escalation)
    assert [t.status for t in mission.tasks] == ["passed", "passed", "passed"]
    assert pod.order.index("Builder:Join") > max(pod.order.index("Builder:Part A"),
                                                 len(pod.order) - 1 - pod.order[::-1].index("PHP/WordPress Developer:Part B"))
    assert (workspace / "b.php").read_text() == "<?php // B again\n" and (workspace / "c.txt").read_text() == "C\n"


def check_batching_rules(base: Path) -> None:
    orca = Orca(chat=lambda m, t: turn("x"), store=MissionStore(base / "rules"))
    from app.platform.orca.models import Mission

    def tasks(*specs) -> Mission:
        m = Mission("ORCA-RULES0000001", "g", str(base))
        m.tasks = [Task(f"T{i}", f"t{i}", "d", files=list(files), acceptance_checks=["grep -q x a"], depends_on=list(deps))
                   for i, (files, deps) in enumerate(specs, start=1)]
        return m

    m = tasks((["a"], []), (["b"], []), (["c"], []), (["d"], []))
    assert [t.task_id for t in orca._batch(m, m.tasks)] == ["T1", "T2", "T3"], "at most three side by side"
    m = tasks((["a"], []), (["a"], []))
    assert [t.task_id for t in orca._batch(m, m.tasks)] == ["T1"], "overlapping files: one at a time"
    m = tasks(([], []), (["b"], []))
    assert [t.task_id for t in orca._batch(m, m.tasks)] == ["T1"], "a task without files runs alone"
    m = tasks((["a"], []), (["b"], ["T1"]))
    assert [t.task_id for t in orca._batch(m, m.tasks)] == ["T1"], "a dependent task waits"
    m = tasks((["./src/x.php"], []), (["src/x.php"], []))
    assert len(orca._batch(m, m.tasks)) == 1, "paths are compared normalised"

    good = [dict(PLAN["tasks"][0]), dict(PLAN["tasks"][1], depends_on=[1])]
    assert plan_problems(good, str(base)) == []
    for bad in ([2], [0], ["1"], [True]):
        problems = plan_problems([dict(PLAN["tasks"][0]), dict(PLAN["tasks"][1], depends_on=bad)], str(base))
        assert any("depends_on" in p for p in problems), (bad, problems)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        check_side_by_side(base)
        check_batching_rules(base)
    print("ORCA PARALLEL CHECK PASSED")


if __name__ == "__main__":
    main()
