"""Deterministic check: Nautilus proposes a repair on a scratch copy, and the proposal is applied
only through the existing approval gate and repair executor (scripted model, no network)."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import mock

import app.platform.services.nautilus_repair_service.proposal as proposal_module
import app.platform.services.repair_executor_service.part_2 as executor_part
from app.platform.agents.repair_executor_check.part_1 import _approved_gate, _blocked_gate, _planned_repair
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


def propose(sandbox: str, model) -> dict:
    with mock.patch.object(proposal_module, "generate_repair_plan_for_workflow", _planned_repair):
        return propose_nautilus_repair(workflow_run_id=RUN_ID, sandbox_root=sandbox, chat=model)


def apply(gate) -> dict:
    with mock.patch.object(executor_part, "assert_repair_apply_allowed", gate), \
            mock.patch.object(executor_part, "generate_repair_plan_for_workflow", _planned_repair):
        return apply_nautilus_repair_proposal(workflow_run_id=RUN_ID)


def check_propose_then_apply(sandbox: Path) -> None:
    scratch_before = set(Path(tempfile.gettempdir()).glob("nautilus-repair-*"))
    result = propose(str(sandbox), fixing_model())
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


def check_stale_and_out_of_plan(sandbox: Path) -> None:
    (sandbox / "src/App.jsx").write_text(BROKEN)
    propose(str(sandbox), fixing_model())
    (sandbox / "src/App.jsx").write_text(BROKEN + "// edited by someone else\n")
    stale = apply(_approved_gate)
    assert stale["apply_status"] == "blocked" and "changed since" in stale["block_reason"], stale

    (sandbox / "src/App.jsx").write_text(BROKEN)
    propose(str(sandbox), fixing_model(extra_write="src/other.js"))
    outside = apply(_approved_gate)
    assert outside["apply_status"] == "blocked" and "src/other.js" in outside["block_reason"], outside
    assert not (sandbox / "src/other.js").exists() and (sandbox / "src/App.jsx").read_text() == BROKEN


def check_blocked_inputs(sandbox: Path) -> None:
    missing = propose(str(sandbox / "does-not-exist"), fixing_model())
    assert missing["proposal_status"] == "blocked" and missing["proposal"] is None, missing
    not_needed = {"repair_plan": {"plan_needed": False}}
    with mock.patch.object(proposal_module, "generate_repair_plan_for_workflow", lambda run_id: not_needed):
        result = propose_nautilus_repair(workflow_run_id=RUN_ID, sandbox_root=str(sandbox), chat=fixing_model())
    assert result["proposal_status"] == "blocked", result
    idle = scripted(turn("I could not find the problem."))
    nothing = propose(str(sandbox), idle)
    assert nothing["proposal_status"] == "no_changes_proposed", nothing["proposal_status"]
    assert _nautilus_next_step("waiting_for_approved_repair_execution", RUN_ID) == "generate_nautilus_repair_proposal"
    assert _nautilus_next_step("self_healing_loop_completed", RUN_ID) is None


def main() -> None:
    reset_nautilus_repair_proposals_for_check()
    reset_repair_execution_history_for_check()
    with tempfile.TemporaryDirectory() as root:
        sandbox = Path(root, "app")
        (sandbox / "src").mkdir(parents=True)
        (sandbox / "src/App.jsx").write_text(BROKEN)
        (sandbox / "package.json").write_text('{"name": "demo"}\n')
        check_propose_then_apply(sandbox)
        check_stale_and_out_of_plan(sandbox)
        check_blocked_inputs(sandbox)
    reset_nautilus_repair_proposals_for_check()
    reset_repair_execution_history_for_check()
    print("NAUTILUS REPAIR FLOW CHECK PASSED")


if __name__ == "__main__":
    main()
