"""Check for the decision step (from the step 6 test drive): an architect that needs a business decision
asks instead of guessing; the mission waits as awaiting_decision; the founder's answers are validated,
recorded, given to the architect and every builder, and planning continues; questions are capped at
two rounds; the Mission Control API exposes questions and takes answers."""
from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from app.platform.auth.service import _sign_claims
from app.platform.orca import MissionStore, Orca, api_service
from app.platform.orca.orca_check import PASS, Pod, finish, write

ASK = {"summary": "Membership isn't defined in the shop.", "tasks": [],
       "open_questions": ["How does the shop know a customer is a member (a login, a member code, or a list of emails)?"]}
PLAN = {"summary": "Apply the discount for customers on the member email list.", "tasks": [
    {"title": "Member discount", "description": "Members from members.json get 10% off.", "specialty": "backend",
     "files": ["pricing.py"], "acceptance_checks": ["grep -q members pricing.py"]}]}


def mission_in(base: Path, name: str, pod: Pod):
    apps = base / "apps"
    (apps / name).mkdir(parents=True)
    orca = Orca(chat=pod, store=MissionStore(base / f"{name}-missions"), sandbox_base=apps)
    return orca, orca.start_mission("Members get 10% off", str(apps / name))


def check_flow(base: Path) -> None:
    pod = Pod({"Software Architect": [*finish("q", ASK), *finish("p", PLAN)],
               "Builder": [*write("b", "pricing.py", "members = []\n", "done")], "QA Lead": [*finish("qa", PASS)]})
    orca, mission = mission_in(base, "shop", pod)
    mission = orca.run(mission.mission_id)
    assert mission.status == "awaiting_decision" and mission.questions == ASK["open_questions"], mission.status
    assert mission.tasks == [] and not pod.briefings["Builder"], "nothing built before answers"
    assert "don't guess" in pod.briefings["Software Architect"][0]
    for bad in ([], [""], ["a", "b"], ["x" * 2001]):
        try:
            orca.answer_questions(mission.mission_id, bad)
            raise AssertionError(f"bad answers accepted: {bad!r}")
        except ValueError:
            pass
    mission = orca.answer_questions(mission.mission_id, ["Customers on the member email list in members.json"])
    assert mission.status == "planning" and mission.questions == [] and mission.answers[0]["answer"].startswith("Customers")
    mission = orca.run(mission.mission_id)
    assert mission.status == "awaiting_execution_approval" and len(mission.tasks) == 1, mission.status
    replan = pod.briefings["Software Architect"][-1]
    assert "Decisions from the client" in replan and "members.json" in replan
    orca.decide_execution(mission.mission_id, approved=True)
    mission = orca.run(mission.mission_id)
    assert mission.status == "complete", (mission.status, mission.escalation)
    assert "members.json" in pod.briefings["Builder"][0], "builders get the decisions too"
    try:
        orca.answer_questions(mission.mission_id, ["late"])
        raise AssertionError("answers accepted when no questions are open")
    except ValueError:
        pass


def check_round_limit(base: Path) -> None:
    pod = Pod({"Software Architect": [*finish("a", ASK), *finish("b", ASK), *finish("c", ASK), *finish("p", PLAN)]})
    orca, mission = mission_in(base, "rounds", pod)
    orca.run(mission.mission_id)
    orca.answer_questions(mission.mission_id, ["A list of emails"])
    mission = orca.run(mission.mission_id)
    assert mission.status == "awaiting_decision", "a second round is allowed"
    orca.answer_questions(mission.mission_id, ["members.json"])
    mission = orca.run(mission.mission_id)
    assert mission.status == "awaiting_execution_approval", f"third round: questions ignored, the plan is made: {mission.status}"
    assert sum(1 for e in mission.events if e["event"] == "questions_asked") == 2, "never more than two rounds"
    assert "leave open_questions empty" in pod.briefings["Software Architect"][-1]


def check_reviewer_asks(base: Path) -> None:
    """The test drive's case: the plan looked complete, but QA finds the task needs a decision."""
    ask = {"verdict": "FAIL", "evidence": "Anyone can claim the member price with ?member=1.",
           "issues": [{"severity": "blocker", "detail": "Membership comes from the request."}],
           "decision_needed": "How does the shop know a customer is a member?"}
    pod = Pod({"Software Architect": [*finish("p", PLAN), *finish("p2", PLAN)],
               "Builder": [*write("b1", "pricing.py", "member = request.member\n", "trusts the flag"),
                           *write("b2", "pricing.py", "members = load('members.json')\n", "uses the member list")],
               "QA Lead": [*finish("q1", ask), *finish("q2", PASS)]})
    orca, mission = mission_in(base, "review-asks", pod)
    orca.run(mission.mission_id)
    orca.decide_execution(mission.mission_id, approved=True)
    mission = orca.run(mission.mission_id)
    assert mission.status == "awaiting_decision", (mission.status, mission.escalation)
    assert mission.questions == [ask["decision_needed"]] and mission.tasks[0].attempts == 1, "asked after one attempt"
    assert mission.escalation is None, "a question is not an escalation"
    assert "decision_needed" in pod.briefings["QA Lead"][0], "reviewers are told they may ask"
    mission = orca.answer_questions(mission.mission_id, ["Customers on the member email list in members.json"])
    assert mission.status == "planning" and mission.tasks == [], "the unfinished task is re-planned with the decision"
    assert mission.events[-1]["replanned"][0]["task"] == "T1"
    mission = orca.run(mission.mission_id)
    assert "Decisions from the client" in pod.briefings["Software Architect"][-1], "the architect re-plans with the answer"
    assert mission.status == "complete", (mission.status, mission.escalation)
    assert "members.json" in pod.briefings["Builder"][-1] and "members.json" in pod.briefings["QA Lead"][-1]


def check_review_fixes(base: Path) -> None:
    from app.platform.orca import handoffs
    from app.platform.orca.models import Mission, Task

    # A question with only non-blocking issues still stops the task (it is not turned into a PASS).
    ask = {"verdict": "FAIL", "evidence": "e", "decision_needed": "Which payment provider?",
           "issues": [{"severity": "critical", "detail": "Old admin page has no login", "introduced_by_change": False}]}
    pod = Pod({"Software Architect": [*finish("p", PLAN)], "Builder": [*write("b", "pricing.py", "members = []\n", "done")],
               "QA Lead": [*finish("q", PASS)], "Security Reviewer": [*finish("s", ask)]})
    apps = base / "fixes-apps"
    (apps / "shop").mkdir(parents=True)
    orca = Orca(chat=pod, store=MissionStore(base / "fixes-missions"), sandbox_base=apps)
    mission = orca.start_mission("Members get 10% off", str(apps / "shop"))
    mission.sandboxed = True  # security review runs for client missions
    orca.store.save(mission)
    from app.platform.clients.work_check import FakeSandbox
    from app.platform.orca import sandbox_commands

    with mock.patch.object(sandbox_commands, "run_in_sandbox", FakeSandbox()):  # client missions run commands in the sandbox
        orca.run(mission.mission_id)
        orca.decide_execution(mission.mission_id, approved=True)
        mission = orca.run(mission.mission_id)
    assert mission.status == "awaiting_decision" and mission.questions == ["Which payment provider?"], mission.status

    # UX reviewers see the answers too.
    m = Mission("ORCA-UXDECIDE0001", "g", str(base))
    m.answers = [{"question": "Who is a member?", "answer": "Emails in members.json"}]
    assert "members.json" in handoffs.ux_review_assignment(m, Task("T1", "t", "d"), {"summary": "s"}, {"evidence": "e"})

    # Rounds count answered cycles; questions raised together join the waiting round.
    m.events = [{"event": "questions_asked", "task": "T1"}, {"event": "questions_asked", "task": "T2"},
                {"event": "questions_asked", "task": "T3"}]
    assert handoffs.answered_rounds(m) == 0
    joiner = Orca(chat=Pod({}), store=MissionStore(base / "join"))
    m.status, m.questions = "awaiting_decision", ["q1", "q2"]
    m.events += [{"event": "questions_answered"}, {"event": "questions_asked", "task": "T4"}, {"event": "questions_answered"}]
    t5 = Task("T5", "t", "d", attempts=1, handoffs=[{"attempt": 1, "kind": "qa_verdict", "decision_needed": "q3"}])
    assert joiner._ask_instead(m, t5), "joins the round already waiting, even at the cap"
    assert m.questions == ["q1", "q2", "q3"]

    # Only the latest attempt's questions count (an older attempt with the same number never re-asks).
    stale = Task("T1", "t", "d", attempts=1, handoffs=[
        {"attempt": 1, "kind": "build"}, {"attempt": 1, "kind": "ux_verdict", "decision_needed": "Old question?"},
        {"attempt": 1, "kind": "build"}, {"attempt": 1, "kind": "qa_verdict", "verdict": "FAIL"}])
    fresh = Mission("ORCA-STALEQ000001", "g", str(base))
    fresh.status = "building"
    assert not joiner._ask_instead(fresh, stale) and fresh.questions == [], "a stale question is not asked again"

    # Re-planning keeps finished tasks and numbers new ones after them.
    pod = Pod({"Software Architect": [*finish("r", {"summary": "s", "tasks": [dict(PLAN["tasks"][0], title="Email check")]})]})
    apps = base / "keep-apps"
    (apps / "shop").mkdir(parents=True)
    orca = Orca(chat=pod, store=MissionStore(base / "keep-missions"), sandbox_base=apps)
    kept = orca.start_mission("Members get 10% off", str(apps / "shop"), execution_approved=True)
    kept.tasks = [Task("T1", "Pricing", "d", ["pricing.py"], ["grep -q x pricing.py"], status="passed",
                       handoffs=[{"attempt": 1, "kind": "build", "summary": "discount maths done"}]),
                  Task("T2", "Checkout", "d", ["checkout.py"], ["grep -q x checkout.py"], attempts=1)]
    kept.status, kept.questions = "awaiting_decision", ["How do we verify members?"]
    kept.record("questions_asked", task="T2", questions=kept.questions)
    orca.store.save(kept)
    orca.answer_questions(kept.mission_id, ["Email on the member list"])
    kept = orca.run(kept.mission_id)
    assert [(t.task_id, t.title) for t in kept.tasks] == [("T1", "Pricing"), ("T2", "Email check")], \
        [(t.task_id, t.title) for t in kept.tasks]
    assert kept.tasks[0].status == "passed", "finished work is kept, not redone"
    brief = pod.briefings["Software Architect"][-1]
    assert "Already done" in brief and "discount maths done" in brief and "Email on the member list" in brief


def check_api(base: Path) -> None:
    from app.platform.server import app

    pod = Pod({"Software Architect": [*finish("q", ASK), *finish("p", PLAN)]})
    store = MissionStore(base / "api-missions")
    apps = base / "api-apps"
    (apps / "shop").mkdir(parents=True)
    factory = lambda: Orca(chat=pod, store=store, sandbox_base=apps)  # noqa: E731
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).replace(microsecond=0).isoformat()
    token = _sign_claims({"sub": "founder@example.com", "role": "founder", "exp": expires})
    http = TestClient(app)

    def post(path, **body):
        return http.post(f"/mission-control/orca/{path}", json={"token": token, **body}).json()

    from app.platform.orca import runner

    with mock.patch.object(api_service, "_orca_factory", factory), \
            mock.patch.object(api_service, "APPROVED_SANDBOX_ROOT_BASE", apps):
        started = post("start", goal="Members get 10% off", workspace="shop")
        mid = started["mission"]["mission_id"]
        runner.wait_for(mid, 30)
        listed = {m["mission_id"]: m for m in post("missions")["missions"]}[mid]
        assert listed["status"] == "awaiting_decision" and listed["questions"] == ASK["open_questions"]
        assert http.post("/mission-control/orca/answer", json={"mission_id": mid, "answers": ["x"]}).json()["status"] == "unauthorized"
        assert post("answer", mission_id=mid, answers="not a list")["status"] == "error"
        assert post("answer", mission_id=mid, answers=[""])["status"] == "error"
        answered = post("answer", mission_id=mid, answers=["Customers on the member email list"])
        assert answered["status"] == "ok", answered
        runner.wait_for(mid, 30)
        assert store.load(mid).status == "awaiting_execution_approval"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        check_flow(base)
        check_round_limit(base)
        check_reviewer_asks(base)
        check_review_fixes(base)
        check_api(base)
    print("ORCA DECISIONS CHECK PASSED")


if __name__ == "__main__":
    main()
