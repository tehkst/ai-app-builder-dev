from __future__ import annotations

from typing import Any, Dict

from app.platform.agents.registry import AgentDefinition, register_agent
from app.platform.agents.factory import agent_factory_handler


def _goal(task: Dict[str, Any]) -> str:
    input_payload = task.get("input_payload") or {}
    return str(input_payload.get("goal") or task.get("description") or task.get("title") or "No goal provided")


def architect_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    return {
        "success": True,
        "agent_id": "architect_agent",
        "message": "Architect Agent V1 produced an architecture plan.",
        "goal": goal,
        "architecture_plan": {
            "frontend": "React or generated UI layer",
            "backend": "FastAPI service layer",
            "database": "SQLAlchemy-managed relational database",
            "auth": "User authentication and role-based access control",
            "core_modules": [
                "data models",
                "API routes",
                "service layer",
                "validation layer",
                "tests",
            ],
            "next_recommended_task": "builder_task",
        },
    }


def builder_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    return {
        "success": True,
        "agent_id": "builder_agent",
        "message": "Builder Agent V1 produced an implementation plan.",
        "goal": goal,
        "implementation_plan": {
            "files_to_create": [
                "models.py",
                "schemas.py",
                "services.py",
                "routes.py",
                "tests.py",
            ],
            "safe_mode": True,
            "writes_code": False,
            "reason": "V1 only plans implementation. Actual file-writing will require approval and sandbox execution.",
            "next_recommended_task": "reviewer_task",
        },
        "generated_files": [
            {
                "path": "app/generated/models.py",
                "language": "python",
                "purpose": "SQLAlchemy data models for the generated application.",
                "content_preview": "Define generated application database models here.",
                "write_status": "preview_only",
            },
            {
                "path": "app/generated/schemas.py",
                "language": "python",
                "purpose": "Pydantic request and response schemas for the generated application.",
                "content_preview": "Define generated application API schemas here.",
                "write_status": "preview_only",
            },
            {
                "path": "app/generated/services.py",
                "language": "python",
                "purpose": "Business logic service layer for the generated application.",
                "content_preview": "Define generated application service functions here.",
                "write_status": "preview_only",
            },
            {
                "path": "app/generated/routes.py",
                "language": "python",
                "purpose": "FastAPI routes for the generated application.",
                "content_preview": "Define generated application API routes here.",
                "write_status": "preview_only",
            },
            {
                "path": "tests/generated/test_generated_app.py",
                "language": "python",
                "purpose": "Smoke tests for the generated application.",
                "content_preview": "Define generated application smoke tests here.",
                "write_status": "preview_only",
            },
        ],
    }


def reviewer_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    return {
        "success": True,
        "agent_id": "reviewer_agent",
        "message": "Reviewer Agent V1 produced a review checklist.",
        "goal": goal,
        "review_checklist": [
            "Validate architecture matches user goal",
            "Check security-sensitive operations",
            "Check database model consistency",
            "Check API route naming",
            "Check approval requirement for risky actions",
            "Check tests are defined before deployment",
        ],
        "next_recommended_task": "test_task",
    }


def validation_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    return {
        "success": True,
        "agent_id": "test_agent",
        "message": "Test Agent V1 produced a validation plan.",
        "goal": goal,
        "validation_plan": {
            "compile_checks": True,
            "release_gate": "fast",
            "api_smoke_tests": True,
            "manual_approval_required_before_deployment": True,
        },
    }


def register_specialist_agents() -> None:
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
            agent_id="reviewer_agent",
            name="Reviewer Agent",
            description="Reviews planned or generated work for quality and safety.",
            capabilities=["reviewer_task"],
            handler=reviewer_agent_handler,
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


register_specialist_agents()
