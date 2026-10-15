"""Mission and task state for Orca. Plain dataclasses, serialised to JSON by store.py."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

MAX_ATTEMPTS = 3  # Dev↔QA attempts per task before escalation (NEXUS rule)

# Mission lifecycle:
# planning -> [awaiting_execution_approval] -> building -> integration
#          -> complete | complete_unverified | escalated | failed
# Any working status can become `paused` (AI provider unavailable); `run` resumes it without
# using up a Dev↔QA attempt. `retry` sends an escalated task back for another round.
TERMINAL_STATUSES = {"complete", "complete_unverified", "escalated", "failed"}
EXECUTION_DECISIONS = ("pending", "approved", "declined", "not_needed")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    files: List[str] = field(default_factory=list)
    acceptance_checks: List[str] = field(default_factory=list)
    status: str = "pending"  # pending | passed | escalated
    attempts: int = 0
    handoffs: List[Dict[str, Any]] = field(default_factory=list)

    def latest_qa_feedback(self) -> Optional[Dict[str, Any]]:
        for handoff in reversed(self.handoffs):
            if handoff.get("kind") == "qa_verdict" and handoff.get("verdict") == "FAIL":
                return handoff
        return None


@dataclass
class Mission:
    mission_id: str
    goal: str
    workspace_root: str
    status: str = "planning"
    execution_approval: str = "pending"
    plan_summary: str = ""
    tasks: List[Task] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    escalation: Optional[Dict[str, Any]] = None
    integration: Optional[Dict[str, Any]] = None
    paused_reason: Optional[str] = None
    resume_status: Optional[str] = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    @property
    def finished(self) -> bool:
        return self.status in TERMINAL_STATUSES

    @property
    def execution_allowed(self) -> bool:
        return self.execution_approval == "approved"

    def record(self, event: str, **details: Any) -> None:
        self.events.append({"at": now_iso(), "event": event, **details})
        self.updated_at = now_iso()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Mission":
        values = dict(data)
        values["tasks"] = [Task(**task) for task in values.get("tasks") or []]
        return cls(**values)
