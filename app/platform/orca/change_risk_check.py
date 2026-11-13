"""Check the change-risk gate (orca/change_risk.py): the levels and plain-language reasons for a plan
on a sample codebase, the Codebase Map's parts and outside services, the assessment saved when a plan
waits for approval, the typed phrase needed to approve a high-risk plan (engine, API and CLI), the
risk recorded with the decision, and a crash in the check never blocking the work. Scripted
architect; no network."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from app.platform.codebase_map.sample import write_sample
from app.platform.orca import MissionStore, Orca, api_service, change_risk
from app.platform.orca.orca_check import Pod, finish


def task(*files: str, status: str = "pending") -> SimpleNamespace:
    return SimpleNamespace(files=list(files), status=status)


def check_levels(root: Path) -> None:
    low = change_risk.assess(str(root), [task("web/src/components/Unused.tsx")])
    assert low["level"] == "low" and low["dependents"] == 0, low
    assert low["reasons"] == ["Nothing else in the code depends on the files it changes.",
                              "No tests cover web/src/components/Unused.tsx, so a mistake there may go unnoticed."], low

    reach = change_risk.assess(str(root), [task("web/src/lib/api.ts")])
    assert reach["dependents"] >= 2 and reach["entry_points"], reach
    assert any("depend on the files it changes" in r for r in reach["reasons"]), reach
    assert any("No tests cover web/src/lib/api.ts" in r for r in reach["reasons"]), "untested code is called out"
    assert reach["level"] == "medium", reach

    for files, area in ((["api/app/payments.py"], "payments"), (["api/app/settings.py"], "secrets and settings"),
                        (["api/app/auth/login.py"], "sign-in and accounts"), (["db/migrations/0002_orders.sql"], "database structure"),
                        ([".github/workflows/deploy.yml"], "deployment")):
        high = change_risk.assess(str(root), [task(*files)])
        assert high["level"] == "high" and area in high["areas"], (files, high)
        assert any(r.startswith(f"Touches {area}") for r in high["reasons"]), high
        assert change_risk.ACK_PHRASE in high["headline"] and change_risk.needs_ack(high)

    admin = change_risk.assess(str(root), [task("plugin/js/admin.js")])
    assert admin["level"] == "medium" and admin["areas"] == ["admin"], admin
    unnamed = change_risk.assess(str(root), [task("web/src/components/Unused.tsx"), task()])
    assert unnamed["level"] == "medium" and any("doesn't say which files 1 task" in r for r in unnamed["reasons"]), unnamed
    done = change_risk.assess(str(root), [task("api/app/payments.py", status="passed"), task("web/src/components/Unused.tsx")])
    assert done["level"] == "low", "finished tasks from an earlier round don't count"
    outside = change_risk.assess(str(root), [task("../../etc/passwd", "/web/src/components/Unused.tsx")])
    assert outside["files"]["changed"] == ["web/src/components/Unused.tsx"] and not outside["files"]["new"], outside

    # With a Codebase Map: the part names, and code that talks to Stripe counts as payments.
    context = {"api/app/routes/orders.py": {"part": "Main server", "services": ["Stripe"]}}
    mapped = change_risk.assess(str(root), [task("api/app/routes/orders.py")], context)
    assert mapped["parts"] == ["Main server"] and mapped["services"] == ["Stripe"] and mapped["level"] == "high", mapped
    assert "Code that talks to Stripe is involved." in mapped["reasons"]

    with mock.patch("app.platform.impact_map.build_map", side_effect=OSError("disk")):
        broken = change_risk.assess_safely(str(root), [task("x.py")])
    assert broken["level"] == "unknown" and not change_risk.needs_ack(broken), "a failing check never blocks the work"


RISKY = {"summary": "Take card payments at checkout.", "tasks": [
    {"title": "Add the payment step", "description": "Create api/app/payments.py calling Stripe.",
     "specialty": "backend", "files": ["api/app/payments.py"], "acceptance_checks": ["grep -q Stripe api/app/payments.py"]}]}


def check_gate(base: Path) -> None:
    from app.platform.auth.service import _sign_claims

    workspace = write_sample(base / "shop")
    store = MissionStore(base / "missions")
    orca = Orca(chat=Pod({"Software Architect": finish("p1", RISKY)}), store=store, sandbox_base=base)
    mission = orca.run(orca.start_mission("Take card payments", str(workspace)).mission_id)
    assert mission.status == "awaiting_execution_approval", mission.status
    assert mission.change_risk["level"] == "high" and "payments" in mission.change_risk["areas"], mission.change_risk
    assert any(e["event"] == "risk_assessed" and e["level"] == "high" for e in mission.events)
    summary = api_service._summary(mission)["risk"]
    assert summary["needs_ack"] and summary["ack_phrase"] == change_risk.ACK_PHRASE and summary["reasons"], summary

    try:
        orca.decide_execution(mission.mission_id, approved=True)
        raise AssertionError("a high-risk plan was approved without the typed phrase")
    except ValueError as exc:
        assert change_risk.ACK_PHRASE in str(exc), exc

    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).replace(microsecond=0).isoformat()
    token = _sign_claims({"sub": "founder@example.com", "role": "founder", "exp": expires})
    with mock.patch.object(api_service, "_orca_factory", lambda: orca), mock.patch.object(api_service, "_launch", lambda m: False):
        wrong = api_service.decide_orca_execution({"token": token, "mission_id": mission.mission_id, "approved": True,
                                                   "risk_ack": "yes"})
        assert wrong["status"] != "ok" and "high risk" in wrong["error"], wrong
        ok = api_service.decide_orca_execution({"token": token, "mission_id": mission.mission_id, "approved": True,
                                                "risk_ack": change_risk.ACK_PHRASE})
    assert ok["status"] == "ok" and ok["mission"]["execution_approval"] == "approved", ok
    decided = [e for e in store.load(mission.mission_id).events if e["event"] == "execution_decided"][-1]
    assert decided["risk_level"] == "high" and decided["risk_acknowledged"] and decided["decided_by"] == "founder@example.com"

    # Declining never needs the phrase; neither does a low-risk plan.
    other = Orca(chat=Pod({"Software Architect": finish("p2", RISKY)}), store=store, sandbox_base=base)
    second = other.run(other.start_mission("Take card payments", str(write_sample(base / "shop2"))).mission_id)
    assert other.decide_execution(second.mission_id, approved=False).execution_approval == "declined"
    calm = {"summary": "Tidy a component.", "tasks": [{**RISKY["tasks"][0], "files": ["web/src/components/Unused.tsx"]}]}
    quiet = Orca(chat=Pod({"Software Architect": finish("p3", calm)}), store=store, sandbox_base=base)
    third = quiet.run(quiet.start_mission("Tidy", str(write_sample(base / "shop3"))).mission_id)
    assert third.change_risk["level"] == "low" and quiet.decide_execution(third.mission_id, approved=True).execution_allowed

    from app.platform.orca.__main__ import main as cli

    cli_orca = Orca(chat=Pod({"Software Architect": finish("p4", RISKY)}), store=store, sandbox_base=base)
    fourth = cli_orca.run(cli_orca.start_mission("Take card payments", str(write_sample(base / "shop4"))).mission_id)
    assert fourth.status == "awaiting_execution_approval" and change_risk.needs_ack(fourth.change_risk)
    with mock.patch("app.platform.orca.__main__.Orca", lambda: SimpleNamespace(
            decide_execution=cli_orca.decide_execution, run=lambda mission_id: store.load(mission_id), store=store)):
        assert cli(["approve", fourth.mission_id]) == 2, "the CLI refuses a high-risk plan without the flag"
        assert cli(["approve", fourth.mission_id, "--accept-high-risk"]) == 0
    assert store.load(fourth.mission_id).execution_allowed


def check_alert_text() -> None:
    from app.platform.orca import alerts
    from app.platform.orca.models import Mission

    waiting = Mission("ORCA-RISK00000001", "Pay", "/w", status="awaiting_execution_approval", change_risk={"level": "high"})
    assert alerts.message(waiting).endswith("Risk: high."), alerts.message(waiting)
    calm = Mission("ORCA-RISK00000002", "Tidy", "/w", status="awaiting_execution_approval", change_risk={"level": "low"})
    assert "Risk" not in alerts.message(calm)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        os.environ.setdefault("ORCA_ALERTS", "")
        check_levels(write_sample(base / "sample"))
        check_gate(base)
        check_alert_text()
    print("ORCA CHANGE RISK CHECK PASSED")


if __name__ == "__main__":
    main()
