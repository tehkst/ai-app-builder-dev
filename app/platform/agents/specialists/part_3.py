from __future__ import annotations

from app.platform.agents.registry import AgentDefinition, register_agent
from app.platform.agents.factory import agent_factory_handler
from app.platform.agents.management_agents import (
    ceo_agent_handler,
    cto_agent_handler,
    engineering_manager_agent_handler,
    backend_manager_agent_handler,
    frontend_manager_agent_handler,
    database_manager_agent_handler,
    quality_manager_agent_handler,
)


def register_specialist_agents() -> None:
    for agent_id, name, capability, handler, description in [
        ("ceo_agent", "CEO Agent", "ceo_task", ceo_agent_handler, "Evaluates whether a requested build aligns with business goals and founder intent."),
        ("cto_agent", "CTO Agent", "cto_task", cto_agent_handler, "Evaluates architecture decisions for technical soundness and strategic direction."),
        ("engineering_manager_agent", "Engineering Manager Agent", "engineering_manager_task", engineering_manager_agent_handler, "Evaluates whether an architecture plan is buildable and appropriately scoped."),
        ("backend_manager_agent", "Backend Manager Agent", "backend_manager_task", backend_manager_agent_handler, "Evaluates generated backend/API implementation quality."),
        ("frontend_manager_agent", "Frontend Manager Agent", "frontend_manager_task", frontend_manager_agent_handler, "Evaluates generated frontend/UI implementation quality."),
        ("database_manager_agent", "Database Manager Agent", "database_manager_task", database_manager_agent_handler, "Evaluates generated data model and schema quality."),
        ("quality_manager_agent", "Quality Manager Agent", "quality_manager_task", quality_manager_agent_handler, "Evaluates review/test artifacts for release readiness."),
    ]:
        register_agent(
            AgentDefinition(
                agent_id=agent_id,
                name=name,
                description=description,
                capabilities=[capability],
                handler=handler,
            )
        )
    register_agent(
        AgentDefinition(
            agent_id="architect_agent",
            name="Architect Agent",
            description="Creates architecture plans for generated applications.",
            capabilities=["architect_task"],
            handler=architect_agent_handler,
        )
    )
    register_agent(
        AgentDefinition(
            agent_id="builder_agent",
            name="Builder Agent",
            description="Creates implementation plans before code generation.",
            capabilities=["builder_task"],
            handler=builder_agent_handler,
            requires_approval_for_new_tasks=True,
        )
    )
    register_agent(
        AgentDefinition(
            agent_id="database_builder_agent",
            name="Database Builder Agent",
            description="Creates database and data-model implementation previews.",
            capabilities=["database_builder_task"],
            handler=database_builder_agent_handler,
            requires_approval_for_new_tasks=True,
        )
    )
    register_agent(
        AgentDefinition(
            agent_id="backend_builder_agent",
            name="Backend Builder Agent",
            description="Creates backend service and route implementation previews.",
            capabilities=["backend_builder_task"],
            handler=backend_builder_agent_handler,
            requires_approval_for_new_tasks=True,
        )
    )
    register_agent(
        AgentDefinition(
            agent_id="frontend_builder_agent",
            name="Frontend Builder Agent",
            description="Creates frontend implementation previews.",
            capabilities=["frontend_builder_task"],
            handler=frontend_builder_agent_handler,
            requires_approval_for_new_tasks=True,
        )
    )
    register_agent(
        AgentDefinition(
            agent_id="reviewer_agent",
            name="Reviewer Agent",
            description="Reviews planned or generated work for quality and safety.",
            capabilities=["reviewer_task"],
            handler=reviewer_agent_handler,
        )
    )
    register_agent(
        AgentDefinition(
            agent_id="code_steward_agent",
            name="Code Steward Agent",
            description="Reviews platform code modularity and recommends safe refactors.",
            capabilities=["code_steward_task", "modularity_review_task"],
            handler=code_steward_agent_handler,
        )
    )
    register_agent(
        AgentDefinition(
            agent_id="agent_factory_agent",
            name="Agent Factory Agent",
            description="Proposes new specialist agents when a project needs capabilities not covered by existing agents.",
            capabilities=["agent_factory_task", "propose_agent"],
            handler=agent_factory_handler,
            requires_approval_for_new_tasks=True,
        )
    )
    register_agent(
        AgentDefinition(
            agent_id="test_agent",
            name="Test Agent",
            description="Creates validation plans and later runs tests.",
            capabilities=["test_task", "worker_loop_test"],
            handler=validation_agent_handler,
        )
    )
