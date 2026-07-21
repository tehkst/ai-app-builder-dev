from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from app.platform.events.company_brain_v3 import CompanyBrainV3
from app.platform.events.company_brain_v3_models import (
    MISSION_APPROVAL_REQUIRED,
    MISSION_BLOCKED,
    MISSION_COMPLETED,
)


@dataclass(frozen=True)
class _Output:
    authoritative: bool = True
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = ("event-1",)
    next_best_action: str = "Proceed."
    status: str = "completed"
    disposition: str = "complete"
    next_action: str = "Mission complete."

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "authoritative": self.authoritative,
            "warnings": list(self.warnings),
            "supporting_event_ids": list(self.supporting_event_ids),
        }


@dataclass(frozen=True)
class _Policy(_Output):
    executable_value: bool = True
    approval_value: bool = False

    @property
    def executable(self) -> bool:
        return self.executable_value

    @property
    def approval_required(self) -> bool:
        return self.approval_value


class _Reasoning:
    def __init__(self, output: _Output) -> None:
        self.output = output
        self.calls = []

    def assess_mission(self, mission_id: str):
        self.calls.append(mission_id)
        return self.output


class _Planning:
    def __init__(self, output: _Output) -> None:
        self.output = output
        self.calls = []

    def generate_execution_plan(self, mission_id: str):
        self.calls.append(mission_id)
        return self.output


class _Principles:
    def __init__(self, output: _Policy) -> None:
        self.output = output
        self.calls = []

    def evaluate_plan(self, plan):
        self.calls.append(plan)
        return self.output


class _Execution:
    def __init__(self, output: _Output) -> None:
        self.output = output
        self.calls = []

    def execute_plan(self, plan):
        self.calls.append(plan)
        return self.output


class _Evolution:
    def __init__(self, output: _Output) -> None:
        self.output = output
        self.calls = []

    def evolve(self, run):
        self.calls.append(run)
        return self.output


class _Twin:
    def __init__(self, output: _Output) -> None:
        self.output = output
        self.calls = []

    def build_snapshot(self, mission_id: str):
        self.calls.append(mission_id)
        return self.output


def _brain(policy: _Policy | None = None):
    reasoning = _Reasoning(_Output())
    planning = _Planning(_Output())
    principles = _Principles(policy or _Policy())
    execution = _Execution(_Output())
    evolution = _Evolution(_Output())
    twin = _Twin(_Output())
    brain = CompanyBrainV3(
        mission_reasoning_engine=reasoning,
        planning_engine=planning,
        principle_engine=principles,
        execution_engine=execution,
        evolution_engine=evolution,
        twin_engine=twin,
    )
    return brain, reasoning, planning, principles, execution, evolution, twin


def _check_completed_path() -> None:
    brain, reasoning, planning, principles, execution, evolution, twin = _brain()
    result = brain.run_mission(" mission-1 ")
    assert result.mission_id == "mission-1"
    assert result.status == MISSION_COMPLETED
    assert result.authoritative
    assert result.terminal
    assert result.execution is not None
    assert result.evolution is not None
    assert reasoning.calls == ["mission-1"]
    assert planning.calls == ["mission-1"]
    assert len(principles.calls) == 1
    assert len(execution.calls) == 1
    assert len(evolution.calls) == 1
    assert twin.calls == ["mission-1"]
    serialized = result.as_dict()
    assert serialized["status"] == MISSION_COMPLETED
    assert serialized["terminal"] is True


def _check_policy_stop() -> None:
    denied = _Policy(executable_value=False, authoritative=True)
    brain, _, _, _, execution, evolution, _ = _brain(denied)
    result = brain.run_mission("mission-2")
    assert result.status == MISSION_BLOCKED
    assert result.execution is None
    assert result.evolution is None
    assert execution.calls == []
    assert evolution.calls == []


def _check_approval_stop() -> None:
    approval = _Policy(
        executable_value=False,
        approval_value=True,
        authoritative=True,
    )
    brain, _, _, _, execution, evolution, _ = _brain(approval)
    result = brain.run_mission("mission-3")
    assert result.status == MISSION_APPROVAL_REQUIRED
    assert result.approval_required
    assert result.execution is None
    assert result.evolution is None
    assert execution.calls == []
    assert evolution.calls == []


def _check_validation() -> None:
    brain, *_ = _brain()
    try:
        brain.run_mission(" ")
    except ValueError as error:
        assert str(error) == "mission_id is required"
    else:
        raise AssertionError("blank mission_id must fail")


def main() -> None:
    _check_completed_path()
    _check_policy_stop()
    _check_approval_stop()
    _check_validation()
    print("company brain v3: PASS")


if __name__ == "__main__":
    main()
