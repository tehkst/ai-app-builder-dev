from __future__ import annotations

CREATED = "created"
QUEUED = "queued"
ASSIGNED = "assigned"
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
CANCELLED = "cancelled"

TERMINAL_STATES = {COMPLETED, FAILED, CANCELLED}
ACTIVE_STATES = {CREATED, QUEUED, ASSIGNED, RUNNING}
VALID_STATES = TERMINAL_STATES | ACTIVE_STATES


def is_terminal(state: str) -> bool:
    return state in TERMINAL_STATES


def is_valid_state(state: str) -> bool:
    return state in VALID_STATES
