from __future__ import annotations

from typing import Dict, Optional

from app.platform.pmo.planning_models import EpicItem


EPICS: Dict[str, EpicItem] = {
    "platform_constitution": EpicItem(
        epic_id="platform_constitution",
        program_id="governance",
        title="Platform Constitution",
        status="planned",
        priority=1,
    ),
    "dynamic_delegation": EpicItem(
        epic_id="dynamic_delegation",
        program_id="autonomous_engineering",
        title="Dynamic Delegation Engine",
        status="planned",
        priority=2,
    ),
    "runtime_sandbox": EpicItem(
        epic_id="runtime_sandbox",
        program_id="runtime_operations",
        title="Runtime Sandbox",
        status="planned",
        priority=3,
    ),
}


def all_epics() -> Dict[str, EpicItem]:
    return dict(EPICS)


def get_epic(epic_id: str) -> Optional[EpicItem]:
    return EPICS.get(epic_id)
