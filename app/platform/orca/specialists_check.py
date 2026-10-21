"""Check for step 4c, the specialists: tasks route to the employee for their specialty, client tasks get
a Security Reviewer pass after QA (FAIL goes back to the builder with the findings; an outage redoes
the attempt), the Technical Writer writes the handover, and generated-app missions are unchanged."""
from __future__ import annotations

import tempfile
from pathlib import Path

from app.platform.nautilus.loop_check import turn
from app.platform.orca import MissionStore, Orca, load_workforce
from app.platform.orca.handoffs import PLAN_SCHEMA, SPECIALTIES
from app.platform.orca.orca_check import PASS, Pod, finish, write
from app.platform.orca.workforce import load_planned_hires

ROUTES = {"php": "PHP/WordPress Developer", "upgrade": "Upgrade Specialist", "database": "Database Builder",
          "devops": "DevOps Engineer", "docs": "Technical Writer", "frontend": "Frontend Developer",
          "backend": "Builder", "general": "Builder"}
HANDOVER = {"summary": "Checkout now applies the member discount.", "changes": ["Member prices at checkout"],
            "how_to_test": ["Log in as a member and check the total"], "watch_out": ["Tests were not run."]}
SECURITY_FAIL = {"verdict": "FAIL", "evidence": "Read cart.php.",
                 "issues": [{"severity": "blocker", "detail": "SQL built from $_GET['id'] in cart.php"}]}


def task(title: str, specialty: str, path: str) -> dict:
    return {"title": title, "description": f"Change {path}.", "specialty": specialty, "files": [path],
            "acceptance_checks": [f"grep -q done {path}"]}


def client_orca(base: Path, pod: Pod, name: str):
    area = base / name / "work"
    workspace = area / "job"
    workspace.mkdir(parents=True)
    (workspace / "index.php").write_text("<?php echo 'hi';\n")
    orca = Orca(chat=pod, store=MissionStore(base / name / "missions"))
    mission = orca.start_mission("Fix the shop", str(workspace), client={"client_id": "CL-x", "client_name": "Shop"},
                                 client_base=area, ai=("openai", "gpt-5.5"))
    return orca, mission


def check_hires() -> None:
    team = load_workforce()
    assert len(team.employees) == 12, sorted(team.employees)
    for specialty, name in ROUTES.items():
        employee = team.find(f"build_task:{specialty}") or team.for_responsibility("build_task")
        assert employee.name == name, (specialty, employee.name)
        assert employee.role_prompt.startswith("# " + name.split(" (")[0]), name
        assert employee.permission_mode == "smart" and employee.autonomy_tier == 1, name
    assert set(ROUTES) == set(SPECIALTIES) and PLAN_SCHEMA["properties"]["tasks"]["items"]["properties"]["specialty"]["enum"] == list(SPECIALTIES)
    assert team.for_responsibility("review_security").permission_mode == "read_only"
    assert team.for_responsibility("write_handover").name == "Technical Writer"
    hired = {e.name for e in team.employees.values()}
    assert not hired & {h["name"] for h in load_planned_hires()}, "planned hires must not repeat hired employees"


def check_routing_and_reviews(base: Path) -> None:
    plan = {"summary": "One task per specialist.",
            "tasks": [task(f"{s} work", s, f"{s}.txt") for s in ("php", "upgrade", "database", "devops", "docs")]}
    builders = {name: [*write(f"{name[:3]}1", f"{s}.txt", "done\n", "did it")]
                for s, name in ROUTES.items() if s in ("upgrade", "database", "devops", "docs")}
    builders["PHP/WordPress Developer"] = [*write("php1", "php.txt", "done\n", "first try"),
                                           *write("php2", "php.txt", "done\n", "prepared statement now"),
                                           *write("php3", "php.txt", "done\n", "redone after the outage")]
    pod = Pod({"Software Architect": [*finish("p", plan)], **builders,
               "QA Lead": [x for i in range(7) for x in finish(f"q{i}", PASS)],  # php: 3 attempts (one redone), + 4 tasks
               # php: FAIL first, then outage (attempt redone), then PASS; the others PASS
               "Security Reviewer": [*finish("s1", SECURITY_FAIL), RuntimeError("provider down"), *finish("s2", PASS),
                                     *[x for i in range(4) for x in finish(f"s{i + 3}", PASS)]],
               "Technical Writer": [*finish("w0", HANDOVER)]})
    # The Technical Writer also builds the docs task: its build turns come before the handover.
    pod.scripts["Technical Writer"] = [*builders["Technical Writer"], *finish("w0", HANDOVER)]
    orca, mission = client_orca(base, pod, "routing")
    orca.run(mission.mission_id)
    orca.decide_execution(mission.mission_id, approved=False)
    mission = orca.run(mission.mission_id)
    assert mission.status == "paused" and "security_reviewer" in mission.paused_reason, mission.status
    php = mission.tasks[0]
    assert php.attempts == 1 and [h["kind"] for h in php.handoffs] == ["build", "qa_verdict", "security_verdict"], php.handoffs
    mission = orca.run(mission.mission_id)  # resume after the outage: attempt 2 is redone in full
    assert mission.status == "complete_unverified", (mission.status, mission.escalation)
    php = mission.tasks[0]
    assert php.status == "passed" and php.attempts == 2, (php.status, php.attempts)
    assert [h["employee"] for h in php.handoffs if h["kind"] == "build"] == ["php_developer", "php_developer"]
    retry = pod.briefings["PHP/WordPress Developer"][1]
    assert "Security review of your previous attempt: FAIL" in retry and "$_GET['id']" in retry, retry[:400]
    built_by = {t.specialty: [h["employee"] for h in t.handoffs if h["kind"] == "build"][0] for t in mission.tasks}
    assert built_by == {"php": "php_developer", "upgrade": "upgrade_specialist", "database": "database_builder",
                        "devops": "devops_engineer", "docs": "technical_writer"}, built_by
    assert all(any(h["kind"] == "security_verdict" for h in t.handoffs) for t in mission.tasks)
    assert mission.handover["summary"] == HANDOVER["summary"] and mission.handover["employee"] == "technical_writer"
    assert "NOT run" in pod.briefings["Technical Writer"][-1], "the handover must say tests weren't run"


def check_handover_failure_and_generated_apps(base: Path) -> None:
    plan = {"summary": "s", "tasks": [task("Fix", "general", "a.txt")]}
    pod = Pod({"Software Architect": [*finish("p", plan)], "Builder": [*write("b", "a.txt", "done\n", "ok")],
               "QA Lead": [*finish("q", PASS)], "Security Reviewer": [*finish("s", PASS)],
               "Technical Writer": [turn("I'd rather not.")]})
    orca, mission = client_orca(base, pod, "no-handover")
    orca.run(mission.mission_id)
    orca.decide_execution(mission.mission_id, approved=False)
    mission = orca.run(mission.mission_id)
    assert mission.status == "complete_unverified" and "error" in mission.handover, mission.handover
    assert mission.events[-1]["event"] == "handover_skipped"

    # Generated-app missions: no security review, no handover (the pod has neither role).
    sandbox = base / "apps"
    (sandbox / "demo").mkdir(parents=True)
    pod = Pod({"Software Architect": [*finish("p", plan)], "Builder": [*write("b", "a.txt", "done\n", "ok")],
               "QA Lead": [*finish("q", PASS)]})
    orca = Orca(chat=pod, store=MissionStore(base / "apps-missions"), sandbox_base=sandbox)
    mission = orca.start_mission("Fix", str(sandbox / "demo"))
    orca.run(mission.mission_id)
    orca.decide_execution(mission.mission_id, approved=False)
    mission = orca.run(mission.mission_id)
    assert mission.status == "complete_unverified" and mission.handover is None
    assert [h["kind"] for h in mission.tasks[0].handoffs] == ["build", "qa_verdict"]


def main() -> None:
    check_hires()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        check_routing_and_reviews(base)
        check_handover_failure_and_generated_apps(base)
    print("ORCA SPECIALISTS CHECK PASSED")


if __name__ == "__main__":
    main()
