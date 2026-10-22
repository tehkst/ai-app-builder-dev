"""Orca: the orchestrator of AI Software Factory's AI employees.

An orca pod hunts as a team led by a matriarch who knows every member's role. Orca reads the
workforce (company/workforce/), plans each mission with the architect, runs every task through a
Dev↔QA loop with builders and the QA lead on Nautilus, and keeps the founder's gates. Process
adapted from the NEXUS playbook in agency-agents (MIT). See docs/architecture/orca.md.
"""
from app.platform.orca.engine import Orca
from app.platform.orca.models import MAX_ATTEMPTS, Mission, Task
from app.platform.orca.store import DbMissionStore, MissionStore
from app.platform.orca.workforce import Employee, Workforce, WorkforceError, load_workforce

__all__ = ["MAX_ATTEMPTS", "Employee", "Mission", "MissionStore", "DbMissionStore", "Orca", "Task", "Workforce",
           "WorkforceError", "load_workforce"]
