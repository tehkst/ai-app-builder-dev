from __future__ import annotations

from typing import Any, Dict, List

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


TASK_ARTIFACT_ALLOWLISTS = {
    "backend_contract": {
        "generated/backend/service.py",
        "generated/backend/routes.py",
        "generated/backend/tests/test_routes.py",
    },
    "data_model": {
        "generated/manifest.json",
        "generated/backend/models.py",
        "generated/backend/schemas.py",
        "README.md",
    },
    "frontend_shell": {
        "generated/manifest.json",
        "generated/frontend/App.jsx",
        "generated/frontend/package.json",
        "index.html",
        "styles.css",
        "app.js",
        "README.md",
    },
}


def _goal(task: Dict[str, Any]) -> str:
    input_payload = task.get("input_payload") or {}
    workflow_context = input_payload.get("workflow_context") or {}
    workflow_name = str(workflow_context.get("workflow_name") or "")

    if workflow_name.startswith("Build App: "):
        return workflow_name.removeprefix("Build App: ").strip() or "No goal provided"

    return str(input_payload.get("goal") or task.get("description") or task.get("title") or "No goal provided")


def _source_task_id(task: Dict[str, Any]) -> str:
    input_payload = task.get("input_payload") or {}
    return str(input_payload.get("step_id") or input_payload.get("source_task_id") or "")


def _dependency_context(task: Dict[str, Any]) -> Dict[str, Any]:
    input_payload = task.get("input_payload") or {}
    workflow_context = input_payload.get("workflow_context") or {}

    dependency_outputs = (
        workflow_context.get("dependency_outputs")
        or input_payload.get("dependency_outputs")
        or {}
    )

    source_steps: List[str] = []
    source_agents: List[str] = []

    if isinstance(dependency_outputs, dict):
        items = dependency_outputs.items()
        dependency_count = len(dependency_outputs)
    else:
        items = [("", dependency) for dependency in dependency_outputs]
        dependency_count = len(dependency_outputs)

    for step_key, dependency in items:
        if not isinstance(dependency, dict):
            continue

        step_id = dependency.get("step_id") or step_key
        selected_agent = dependency.get("selected_agent") or {}
        output = dependency.get("output") or {}
        agent_id = selected_agent.get("agent_id") or output.get("agent_id")

        if step_id:
            source_steps.append(str(step_id))
        if agent_id:
            source_agents.append(str(agent_id))

    return {
        "dependency_output_count": dependency_count,
        "source_steps": source_steps,
        "source_agents": source_agents,
        "context_available": dependency_count > 0,
    }


def _filter_generated_files_for_task(source_task_id: str, generated_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    allowlist = TASK_ARTIFACT_ALLOWLISTS.get(source_task_id)
    if not allowlist:
        return generated_files
    return [file_entry for file_entry in generated_files if file_entry.get("path") in allowlist]


def architect_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    input_payload = task.get("input_payload") or {}
    approved_plan = input_payload.get("approved_plan") if isinstance(input_payload.get("approved_plan"), dict) else {}
    requested_evidence = [
        str(item.get("path") if isinstance(item, dict) else item).strip()
        for item in approved_plan.get("affected_files") or []
        if str(item.get("path") if isinstance(item, dict) else item).strip()
        and "to be determined" not in str(item.get("path") if isinstance(item, dict) else item).lower()
    ]
    return {
        "success": True,
        "agent_id": "architect_agent",
        "message": "Architect Agent V1 produced an architecture plan.",
        "goal": goal,
        "architecture_plan": {
            "mission_id": input_payload.get("mission_id"),
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
            "requested_repository_evidence": list(dict.fromkeys(requested_evidence)),
            "evidence_request_reason": "Inspect approved implementation targets and their bounded integration context before code generation.",
            "next_recommended_task": "builder_task",
        },
    }


def builder_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    source_task_id = _source_task_id(task)
    dependency_context = _dependency_context(task)
    generated_files = _filter_generated_files_for_task(source_task_id, build_preview_generated_files(goal))
    files_to_create = [file_entry.get("path") for file_entry in generated_files]
    return {
        "success": True,
        "agent_id": "builder_agent",
        "message": "Builder Agent V100 produced specialist-routed DB-preview artifacts.",
        "goal": goal,
        "source_task_id": source_task_id,
        "dependency_context": dependency_context,
        "implementation_plan": {
            "artifact_profile": "v100_specialist_builder_preview",
            "files_to_create": files_to_create,
            "generated_file_count": len(generated_files),
            "dependency_context_available": dependency_context.get("context_available"),
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
                "V100 routes task graph work through specialist builder capabilities while preserving DB-preview safety. "
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


def database_builder_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    result = builder_agent_handler(task)
    result["agent_id"] = "database_builder_agent"
    result["domain_builder"] = "database"
    result["message"] = "Database Builder Agent V100 produced DB-preview artifacts."
    return result


def backend_builder_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    result = builder_agent_handler(task)
    result["agent_id"] = "backend_builder_agent"
    result["domain_builder"] = "backend"
    result["message"] = "Backend Builder Agent V101 produced DB-preview artifacts."
    return result


def frontend_builder_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    result = builder_agent_handler(task)
    result["agent_id"] = "frontend_builder_agent"
    result["domain_builder"] = "frontend"
    result["message"] = "Frontend Builder Agent V100 produced DB-preview artifacts."
    return result


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


def code_steward_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    return {
        "success": True,
        "agent_id": "code_steward_agent",
        "message": "Code Steward Agent produced a modularity and refactor guard report.",
        "goal": goal,
        "modularity_report": {
            "max_file_size_policy": "Keep platform modules small and split files before they become orchestration bottlenecks.",
            "checks": [
                "Detect oversized modules",
                "Detect duplicated routing or registry logic",
                "Recommend module splits by responsibility",
                "Preserve manifest-driven boundaries",
                "Prevent runtime changes from bypassing validation gates",
            ],
            "writes_code": False,
            "safe_mode": True,
        },
    }


def management_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    return {
        "success": True,
        "agent_id": "management_agent",
        "message": "Management Agent produced a delegation planning report.",
        "goal": goal,
        "delegation_report": {
            "runtime_execution_changed": False,
            "safe_mode": True,
            "writes_code": False,
        },
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
    for agent_id, name, capability in [
        ("ceo_agent", "CEO Agent", "ceo_task"),
        ("cto_agent", "CTO Agent", "cto_task"),
        ("engineering_manager_agent", "Engineering Manager Agent", "engineering_manager_task"),
        ("backend_manager_agent", "Backend Manager Agent", "backend_manager_task"),
        ("frontend_manager_agent", "Frontend Manager Agent", "frontend_manager_task"),
        ("database_manager_agent", "Database Manager Agent", "database_manager_task"),
        ("quality_manager_agent", "Quality Manager Agent", "quality_manager_task"),
    ]:
        register_agent(
            AgentDefinition(
                agent_id=agent_id,
                name=name,
                description="Passive V106 engineering management foundation agent.",
                capabilities=[capability],
                handler=management_agent_handler,
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


register_specialist_agents()
