from __future__ import annotations

from typing import Dict, List, Optional

from app.platform.pmo.models import RoadmapItem


ROADMAP: Dict[str, RoadmapItem] = {
    "v100_multi_agent_workflow": RoadmapItem(
        roadmap_id="v100_multi_agent_workflow",
        title="V100 Multi-Agent Workflow",
        phase="phase_1_foundation",
        status="completed",
        program_id="autonomous_engineering",
        sequence=100,
        depends_on=[],
        completed_in_pr="#149",
    ),
    "v101_specialist_builders": RoadmapItem(
        roadmap_id="v101_specialist_builders",
        title="V101 Specialist Builder Routing",
        phase="phase_1_foundation",
        status="completed",
        program_id="autonomous_engineering",
        sequence=101,
        depends_on=["v100_multi_agent_workflow"],
        completed_in_pr="#150",
    ),
    "v102_agent_manifests": RoadmapItem(
        roadmap_id="v102_agent_manifests",
        title="V102 Agent Manifest System",
        phase="phase_1_foundation",
        status="completed",
        program_id="governance",
        sequence=102,
        depends_on=["v101_specialist_builders"],
        completed_in_pr="#151",
    ),
    "v102_1_manifest_sync": RoadmapItem(
        roadmap_id="v102_1_manifest_sync",
        title="V102.1 Manifest Registry Sync",
        phase="phase_1_foundation",
        status="completed",
        program_id="governance",
        sequence=103,
        depends_on=["v102_agent_manifests"],
        completed_in_pr="#152",
    ),
    "v103_organization_hierarchy": RoadmapItem(
        roadmap_id="v103_organization_hierarchy",
        title="V103 Organization Hierarchy",
        phase="phase_1_foundation",
        status="completed",
        program_id="autonomous_engineering",
        sequence=104,
        depends_on=["v102_1_manifest_sync"],
        completed_in_pr="#153",
    ),
    "v104_engineering_memory": RoadmapItem(
        roadmap_id="v104_engineering_memory",
        title="V104 Engineering Memory",
        phase="phase_1_foundation",
        status="completed",
        program_id="engineering_intelligence",
        sequence=105,
        depends_on=["v103_organization_hierarchy"],
        completed_in_pr="#154",
    ),
    "v105_knowledge_graph": RoadmapItem(
        roadmap_id="v105_knowledge_graph",
        title="V105 Engineering Knowledge Graph",
        phase="phase_1_foundation",
        status="completed",
        program_id="engineering_intelligence",
        sequence=106,
        depends_on=["v104_engineering_memory"],
        completed_in_pr="#155",
    ),
    "v106_engineering_management": RoadmapItem(
        roadmap_id="v106_engineering_management",
        title="V106 Engineering Management",
        phase="phase_1_foundation",
        status="completed",
        program_id="autonomous_engineering",
        sequence=107,
        depends_on=["v105_knowledge_graph"],
        completed_in_pr="#156",
    ),
    "v107a_pmo": RoadmapItem(
        roadmap_id="v107a_pmo",
        title="V107A Program Management Office",
        phase="phase_2_control_plane",
        status="in_progress",
        program_id="autonomous_engineering",
        sequence=108,
        depends_on=["v106_engineering_management"],
    ),
    "v107b_constitution": RoadmapItem(
        roadmap_id="v107b_constitution",
        title="V107B Platform Constitution",
        phase="phase_2_control_plane",
        status="planned",
        program_id="governance",
        sequence=109,
        depends_on=["v107a_pmo"],
    ),
    "v107c_delegation": RoadmapItem(
        roadmap_id="v107c_delegation",
        title="V107C Dynamic Delegation Engine",
        phase="phase_2_control_plane",
        status="planned",
        program_id="autonomous_engineering",
        sequence=110,
        depends_on=["v107a_pmo", "v107b_constitution"],
    ),
    "v107d_runtime": RoadmapItem(
        roadmap_id="v107d_runtime",
        title="V107D Runtime Sandbox",
        phase="phase_2_control_plane",
        status="planned",
        program_id="runtime_operations",
        sequence=111,
        depends_on=["v107b_constitution"],
    ),
    "v107e_self_healing": RoadmapItem(
        roadmap_id="v107e_self_healing",
        title="V107E Self Healing",
        phase="phase_2_control_plane",
        status="planned",
        program_id="runtime_operations",
        sequence=112,
        depends_on=["v107d_runtime"],
    ),
}


def all_roadmap_items() -> Dict[str, RoadmapItem]:
    return dict(ROADMAP)


def get_roadmap_item(roadmap_id: str) -> Optional[RoadmapItem]:
    return ROADMAP.get(roadmap_id)


def roadmap_by_status(status: str) -> List[RoadmapItem]:
    return [item for item in ROADMAP.values() if item.status == status]


def next_roadmap_item() -> Optional[RoadmapItem]:
    candidates = [item for item in ROADMAP.values() if item.status in {"planned", "in_progress"}]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.sequence)[0]
