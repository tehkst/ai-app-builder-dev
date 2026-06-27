from __future__ import annotations

from typing import Dict, Optional

from app.platform.pmo.models import ProgramItem


PROGRAMS: Dict[str, ProgramItem] = {
    "governance": ProgramItem(
        program_id="governance",
        name="Governance & Standards",
        owner_department="governance",
        owner_agent="cto_agent",
        mission="Define and enforce the rules that govern autonomous engineering work.",
        status="active",
        priority=1,
    ),
    "autonomous_engineering": ProgramItem(
        program_id="autonomous_engineering",
        name="Autonomous Engineering",
        owner_department="engineering_management",
        owner_agent="engineering_manager_agent",
        mission="Plan, delegate, and coordinate engineering work across departments.",
        status="active",
        priority=2,
    ),
    "runtime_operations": ProgramItem(
        program_id="runtime_operations",
        name="Runtime & Operations",
        owner_department="platform_operations",
        owner_agent="cto_agent",
        mission="Run, observe, deploy, and recover software safely.",
        status="planned",
        priority=3,
    ),
    "engineering_intelligence": ProgramItem(
        program_id="engineering_intelligence",
        name="Engineering Intelligence",
        owner_department="ai",
        owner_agent="cto_agent",
        mission="Improve reasoning, memory, knowledge graph, and learning capabilities.",
        status="active",
        priority=4,
    ),
    "product_factory": ProgramItem(
        program_id="product_factory",
        name="Product Factory",
        owner_department="product",
        owner_agent="ceo_agent",
        mission="Create reusable product factories and commercial application templates.",
        status="planned",
        priority=5,
    ),
    "customer_success": ProgramItem(
        program_id="customer_success",
        name="Customer Success",
        owner_department="customer_success",
        owner_agent="ceo_agent",
        mission="Capture feedback, support users, and turn customer signals into roadmap inputs.",
        status="planned",
        priority=6,
    ),
    "business_operations": ProgramItem(
        program_id="business_operations",
        name="Business Operations",
        owner_department="business_operations",
        owner_agent="ceo_agent",
        mission="Manage pricing, sales, legal, contracts, licensing, and finance operations.",
        status="planned",
        priority=7,
    ),
}


def all_programs() -> Dict[str, ProgramItem]:
    return dict(PROGRAMS)


def get_program(program_id: str) -> Optional[ProgramItem]:
    return PROGRAMS.get(program_id)
