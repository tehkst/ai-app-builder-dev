"""
Native Coding Agent — durable edit / test / repair loop.

The Native Coding Agent replaces text-only change-set generation with a real
workspace-grounded coding loop. It edits actual files, runs real validation,
diagnoses failures, repairs the same workspace iteratively, and produces a
verified git diff for governed downstream execution.

This module is an orchestration capability that assembles existing platform
services (workspace, governance, model routing, validation engine) into a
coherent coding session. The model is a reasoning engine, not the agent.
"""
from __future__ import annotations

from app.platform.coding_agent.service import CodingAgentService, start_coding_session
from app.platform.coding_agent.models import (
    CodingSessionState,
    EditContract,
    EditOperation,
    FailureEvidence,
    VerifiedDiff,
)

__all__ = [
    "CodingAgentService",
    "CodingSessionState",
    "EditContract",
    "EditOperation",
    "FailureEvidence",
    "VerifiedDiff",
    "start_coding_session",
]
