"""Deterministic check: Nautilus proposes a repair on a scratch copy, and the proposal is applied
only through the existing approval gate and repair executor (scripted model, no network)."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.platform.services.nautilus_repair_service.proposal as proposal_module
import app.platform.services.nautilus_repair_service.sandbox as sandbox_module
import app.platform.services.repair_executor_service.part_2 as executor_part
from app.platform.agents.repair_executor_check.part_1 import _approved_gate, _blocked_gate, _planned_repair
from app.platform.api.app_build.nautilus_repair_routes import router as nautilus_router
from app.platform.api.security import require_platform_admin
from app.platform.nautilus.loop_check import call, scripted, turn
from app.platform.services.nautilus_repair_service import (
    apply_nautilus_repair_proposal, latest_nautilus_proposal, propose_nautilus_repair,
    reset_nautilus_repair_proposals_for_check,
)
from app.platform.services.repair_executor_service import reset_repair_execution_history_for_check
from app.platform.services.self_healing_loop_coordinator_service.part_2 import _nautilus_next_step

RUN_ID = "nautilus-repair-check"
BROKEN = "export default function App() { return <div>broken</div> }}\n"
FIXED = "export default function App() { return <div>fixed</div>; }\n"


def fixing_model(extra_write: str = ""):
    calls = [call("w1", "write_file", path="src/App.jsx", content=FIXED)]
    if extra_write:
        calls.append(call("w2", "write_file", path=extra_write, content="// unrelated\n"))
    return scripted(
        turn("", [call("r1", "read_file", path="src/App.jsx"), call("x1", "run_command", command="node src/App.jsx"),
                  call("g1", "run_command", command="grep -n div src/App.jsx")]),
        turn("", calls),
        turn("Root cause: stray brace in src/App.jsx. Removed it."),
    )


def propose(sandbox: Path, model) -> dict:
    """The sandbox reaches the service only through the workflow resolver, as in production."""
    with mock.patch.object(proposal_module, "generate_repair_plan_for_workflow", _planned_repair), \
            mock.patch.object(sandbox_module, "workspace_root_for_workflow", lambda db, run_id: sandbox):
        return propose_nautilus_repair(db=None, workflow_run_id=RUN_ID, chat=model)


def apply(gate) -> dict:
    with mock.patch.object(executor_part, "assert_repair_apply_allowed", gate), \
            mock.patch.object(executor_part, "generate_repair_plan_for_workflow", _planned_repair):
        return apply_nautilus_repair_proposal(workflow_run_id=RUN_ID)


def check_propose_then_apply(sandbox: Path) -> None:
    scratch_before = set(Path(tempfile.gettempdir()).glob("nautilus-repair-*"))
    result = propose(sandbox, fixing_model())
    proposal = result["proposal"]
    assert result["proposal_status"] == "proposed" and not result["generated_code_execution_performed"], result
    assert (sandbox / "src/App.jsx").read_text() == BROKEN, "proposal must not modify the sandbox"
    assert set(Path(tempfile.gettempdir()).glob("nautilus-repair-*")) == scratch_before, "scratch copy not removed"
    outcomes = {r["name"] + ":" + r["outcome"] for r in proposal["tool_calls"]}
    assert {"read_file:ok", "run_command:denied", "run_command:ok", "write_file:ok"} <= outcomes, outcomes
    [change] = proposal["changes"]
    assert change["path"] == "src/App.jsx" and change["within_plan_candidates"], change
    assert "-export default" in change["diff"] and "+export default" in change["diff"], change["diff"]
    assert "stray brace" in proposal["explanation"], proposal["explanation"]
    assert _nautilus_next_step("waiting_for_approved_repair_execution", RUN_ID) == "apply_nautilus_repair_proposal"

    blocked = apply(_blocked_gate)
    assert blocked["apply_status"] == "blocked" and "approved" in blocked["block_reason"], blocked
    assert (sandbox / "src/App.jsx").read_text() == BROKEN

    applied = apply(_approved_gate)
    assert applied["apply_status"] == "applied", applied
    assert (sandbox / "src/App.jsx").read_text() == FIXED
    assert applied["executor_result"]["operations"][0]["target_relative_path"] == "src/App.jsx"
    assert latest_nautilus_proposal(RUN_ID)["proposal_status"] == "applied"
    again = apply(_approved_gate)
    assert again["apply_status"] == "blocked" and "'applied'" in again["block_reason"], again


def check_stale_concurrent_and_out_of_plan(sandbox: Path) -> None:
    (sandbox / "src/App.jsx").write_text(BROKEN)
    propose(sandbox, fixing_model())
    (sandbox / "src/App.jsx").write_text(BROKEN + "// edited by someone else\n")
    stale = apply(_approved_gate)
    assert stale["apply_status"] == "blocked" and "changed since" in stale["block_reason"], stale

    (sandbox / "src/App.jsx").write_text(BROKEN)
    model = fixing_model()

    def edit_live_sandbox_mid_run(messages, tools):
        if len(model.seen) == 1:  # a person edits the real sandbox while the agent is working
            (sandbox / "src/App.jsx").write_text("// concurrent edit B\n")
        return model(messages, tools)

    edit_live_sandbox_mid_run.seen = model.seen
    racing = propose(sandbox, edit_live_sandbox_mid_run)
    assert racing["proposal_status"] == "sandbox_changed_during_generation", racing["proposal_status"]
    assert racing["proposal"]["diverged_paths"] == ["src/App.jsx"], racing["proposal"]["diverged_paths"]
    refused = apply(_approved_gate)
    assert refused["apply_status"] == "blocked", refused
    assert (sandbox / "src/App.jsx").read_text() == "// concurrent edit B\n", "concurrent edit was overwritten"

    (sandbox / "src/App.jsx").write_text(BROKEN)
    propose(sandbox, fixing_model(extra_write="src/other.js"))
    outside = apply(_approved_gate)
    assert outside["apply_status"] == "blocked" and "src/other.js" in outside["block_reason"], outside
    assert not (sandbox / "src/other.js").exists() and (sandbox / "src/App.jsx").read_text() == BROKEN


def check_blocked_inputs(sandbox: Path, outside_base: Path) -> None:
    missing = propose(sandbox.parent / "does-not-exist", fixing_model())
    assert missing["proposal_status"] == "blocked" and missing["proposal"] is None, missing
    escaped = propose(outside_base, fixing_model())
    assert escaped["proposal_status"] == "blocked" and "approved sandbox base" in escaped["block_reason"], escaped
    not_needed = {"repair_plan": {"plan_needed": False}}
    with mock.patch.object(proposal_module, "generate_repair_plan_for_workflow", lambda run_id: not_needed):
        result = propose_nautilus_repair(db=None, workflow_run_id=RUN_ID, chat=fixing_model())
    assert result["proposal_status"] == "blocked", result
    nothing = propose(sandbox, scripted(turn("I could not find the problem.")))
    assert nothing["proposal_status"] == "no_changes_proposed", nothing["proposal_status"]
    assert _nautilus_next_step("waiting_for_approved_repair_execution", RUN_ID) == "generate_nautilus_repair_proposal"
    assert _nautilus_next_step("self_healing_loop_completed", RUN_ID) is None


def check_apply_route_without_body() -> None:
    api = FastAPI()
    api.include_router(nautilus_router)
    api.dependency_overrides[require_platform_admin] = lambda: True
    response = TestClient(api).post(f"/runs/{RUN_ID}/repair-execution/apply-nautilus-proposal")
    assert response.status_code == 200 and response.json()["apply_status"] == "blocked", response.text


def main() -> None:
    reset_nautilus_repair_proposals_for_check()
    reset_repair_execution_history_for_check()
    with tempfile.TemporaryDirectory() as base, tempfile.TemporaryDirectory() as elsewhere:
        with mock.patch.object(sandbox_module, "APPROVED_SANDBOX_ROOT_BASE", Path(base)):
            sandbox = Path(base, "workflow-sandbox")
            (sandbox / "src").mkdir(parents=True)
            (sandbox / "src/App.jsx").write_text(BROKEN)
            (sandbox / "package.json").write_text('{"name": "demo"}\n')
            check_propose_then_apply(sandbox)
            check_stale_concurrent_and_out_of_plan(sandbox)
            check_blocked_inputs(sandbox, Path(elsewhere))
            check_apply_route_without_body()
    reset_nautilus_repair_proposals_for_check()
    reset_repair_execution_history_for_check()
    print("NAUTILUS REPAIR FLOW CHECK PASSED")


if __name__ == "__main__":
    main()
