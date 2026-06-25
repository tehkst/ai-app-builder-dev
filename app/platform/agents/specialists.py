from __future__ import annotations

from typing import Any, Dict

from app.platform.agents.registry import AgentDefinition, register_agent
from app.platform.agents.factory import agent_factory_handler
from app.platform.agents.specialist_preview_files import build_preview_generated_files


V97_BUILDER_ARTIFACTS = [
    "generated/manifest.json",
    "generated/backend/models.py",
    "generated/backend/schemas.py",
    "generated/backend/service.py",
    "generated/backend/routes.py",
    "generated/backend/tests/test_routes.py",
    "generated/frontend/App.jsx",
    "generated/frontend/package.json",
    "index.html",
    "styles.css",
    "app.js",
    "README.md",
]


def _goal(task: Dict[str, Any]) -> str:
    input_payload = task.get("input_payload") or {}
    workflow_context = input_payload.get("workflow_context") or {}
    workflow_name = str(workflow_context.get("workflow_name") or "")

    if workflow_name.startswith("Build App: "):
        return workflow_name.removeprefix("Build App: ").strip() or "No goal provided"

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
    generated_files = build_preview_generated_files(goal)
    return {
        "success": True,
        "agent_id": "builder_agent",
        "message": "Builder Agent V97 produced a DB-preview application scaffold.",
        "goal": goal,
        "implementation_plan": {
            "artifact_profile": "v97_enterprise_scaffold_preview",
            "files_to_create": V97_BUILDER_ARTIFACTS,
            "generated_file_count": len(generated_files),
            "backend_artifacts": [
                "typed domain model",
                "request/response schemas",
                "service layer",
                "FastAPI route module",
                "pytest route contract",
            ],
            "frontend_artifacts": [
                "React application shell",
                "frontend package manifest",
                "static preview shell",
            ],
            "safe_mode": True,
            "writes_code": False,
            "write_mode": "db_preview_only",
            "reason": (
                "V97 emits production-shaped scaffold artifacts as DB-preview records only. "
                "No disk write, filesystem write, deployment, materialization, dependency install, "
                "or generated-code execution is performed."
            ),
            "next_recommended_task": "reviewer_task",
        },
        "generated_files": generated_files,
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "filesystem_write_performed": False,
        "generated_code_execution_performed": False,
        "external_deployment_performed": False,
        "materialization_performed": False,
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
            "Confirm generated artifacts remain DB-preview only before materialization approval",
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
            "generated_artifact_contract_checks": True,
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
