from __future__ import annotations

from app.platform.pmo.portfolio_registry import all_portfolios, get_portfolio
from app.platform.pmo.program_registry import all_programs, get_program
from app.platform.pmo.roadmap_registry import all_roadmap_items, next_roadmap_item, roadmap_by_status


REQUIRED_PROGRAMS = {
    "governance",
    "autonomous_engineering",
    "runtime_operations",
    "engineering_intelligence",
    "product_factory",
    "customer_success",
    "business_operations",
}

REQUIRED_COMPLETED = {
    "v100_multi_agent_workflow",
    "v101_specialist_builders",
    "v102_agent_manifests",
    "v103_organization_hierarchy",
    "v104_engineering_memory",
    "v105_knowledge_graph",
    "v106_engineering_management",
}


def main() -> None:
    portfolios = all_portfolios()
    programs = all_programs()
    roadmap = all_roadmap_items()

    assert "ai_software_factory" in portfolios, portfolios
    portfolio = get_portfolio("ai_software_factory")
    assert portfolio is not None, portfolios
    assert REQUIRED_PROGRAMS.issubset(set(portfolio.program_ids)), portfolio
    assert REQUIRED_PROGRAMS.issubset(set(programs)), programs

    for program_id, program in programs.items():
        assert program.program_id == program_id, program
        assert program.name, program
        assert program.owner_agent, program
        assert program.mission, program
        assert program.status in {"planned", "active", "completed", "paused"}, program
        assert program.priority > 0, program

    assert REQUIRED_COMPLETED.issubset(set(roadmap)), roadmap
    for roadmap_id, item in roadmap.items():
        assert item.roadmap_id == roadmap_id, item
        assert get_program(item.program_id) is not None, item
        assert item.status in {"planned", "in_progress", "completed", "blocked", "paused"}, item
        for dependency in item.depends_on:
            assert dependency in roadmap, {"item": roadmap_id, "missing_dependency": dependency}

    completed = roadmap_by_status("completed")
    assert len(completed) >= len(REQUIRED_COMPLETED), completed

    next_item = next_roadmap_item()
    assert next_item is not None, roadmap
    assert next_item.roadmap_id == "v107a_pmo", next_item

    print("PMO CHECK PASSED")


if __name__ == "__main__":
    main()
