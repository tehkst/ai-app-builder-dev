from __future__ import annotations

from typing import Any, Dict, List

from app.platform.agents.registry import AgentDefinition, register_agent
from app.platform.agents.factory import agent_factory_handler
from app.platform.services.app_generation_service import (
    generate_app_build_files,
    repair_app_build_files,
    review_app_build_files,
)
from app.platform.architecture_agent.service import create_architecture_decision


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


def _dependency_output_for_step(task: Dict[str, Any], step_id: str) -> Dict[str, Any]:
    """Return the named prior step's own handler_result payload.

    _dependency_context above only summarizes dependency metadata (counts, step
    ids, agent ids). The reviewer needs the builder step's actual generated_files
    and generation.provider, which agent_workflow_context.compact_step_output
    nests under dependency["output"]["handler_result"] (for bridge-executed
    steps) - not directly under dependency["output"].
    """
    input_payload = task.get("input_payload") or {}
    workflow_context = input_payload.get("workflow_context") or {}
    dependency_outputs = (
        workflow_context.get("dependency_outputs")
        or input_payload.get("dependency_outputs")
        or {}
    )

    items = dependency_outputs.items() if isinstance(dependency_outputs, dict) else [("", dependency) for dependency in dependency_outputs]
    for step_key, dependency in items:
        if not isinstance(dependency, dict):
            continue
        if str(dependency.get("step_id") or step_key) == step_id:
            output = dependency.get("output") or {}
            handler_result = output.get("handler_result") if isinstance(output, dict) else None
            if isinstance(handler_result, dict):
                return handler_result
            fallback = output.get("output") if isinstance(output, dict) else None
            return fallback if isinstance(fallback, dict) else {}
    return {}


def _other_provider(provider: Any) -> str:
    return "deepseek" if str(provider or "").strip().lower() == "openai" else "openai"


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
    mission_id = str(input_payload.get("mission_id") or "")
    if not mission_id.startswith("MISSION-"):
        return {
            "success": True,
            "agent_id": "architect_agent",
            "message": "Architect Agent produced a non-authoritative legacy workflow preview.",
            "goal": goal,
            "status": "non-mission-architecture-preview",
            "validation_errors": [],
            "correction_attempted": False,
            "architecture_decision": {},
            "architecture_plan": {
                "mission_id": None,
                "architecture_summary": "Legacy application workflow preview; not authoritative Mission Control architecture evidence.",
                "integration_contracts": [],
                "architecture_constraints": ["A canonical MISSION-* identity and CAPCTX context are required before this output can become authoritative."],
                "requested_repository_evidence": list(dict.fromkeys(requested_evidence)),
                "evidence_request_reason": "Inspect approved implementation targets before generated-application preview work.",
                "required_validation": [],
                "next_recommended_task": "builder_task",
            },
        }
    decision_result = create_architecture_decision({
        "mission_id": mission_id,
        "objective": goal,
        "approved_plan": approved_plan,
        "acceptance_criteria": input_payload.get("acceptance_criteria") or [],
        "affected_domains": input_payload.get("affected_domains") or [],
        "affected_paths": input_payload.get("affected_paths") or requested_evidence,
        "capability_context": input_payload.get("capability_context") or {},
        "repository_evidence": input_payload.get("repository_evidence") or {},
        "existing_constraints": input_payload.get("existing_constraints") or [],
        "proposed_component": input_payload.get("proposed_component"),
        "candidate_artifact": input_payload.get("candidate_artifact"),
        "progress_observer": input_payload.get("progress_observer"),
    })
    artifact = decision_result.get("architecture_decision") or {}
    return {
        "success": bool(decision_result.get("success")),
        "agent_id": "architect_agent",
        "message": "Architect Agent produced a validated platform-aware architecture decision." if decision_result.get("success") else "Architecture decision validation blocked the review.",
        "goal": goal,
        "status": decision_result.get("status"),
        "validation_errors": decision_result.get("validation_errors") or [],
        "correction_attempted": bool(decision_result.get("correction_attempted")),
        "architecture_decision": artifact,
        "architecture_plan": {
            "mission_id": input_payload.get("mission_id"),
            "decision_id": artifact.get("decision_id"),
            "capability_context_id": artifact.get("capability_context_id"),
            "architecture_summary": artifact.get("architecture_summary"),
            "integration_contracts": artifact.get("integration_contracts") or [],
            "architecture_constraints": artifact.get("architecture_constraints") or [],
            "requested_repository_evidence": list(dict.fromkeys(requested_evidence)),
            "evidence_request_reason": "Inspect approved implementation targets and their bounded integration context before code generation.",
            "required_validation": artifact.get("required_validation") or [],
            "next_recommended_task": "engineering_manager_task" if artifact else None,
        },
    }


def builder_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    source_task_id = _source_task_id(task)
    dependency_context = _dependency_context(task)
    input_payload = task.get("input_payload") or {}

    generation = generate_app_build_files(
        app_request=str(input_payload.get("app_request") or goal),
        scope_of_work_markdown=str(input_payload.get("scope_of_work_markdown") or ""),
        acceptance_criteria=input_payload.get("acceptance_criteria") or [],
        out_of_scope=input_payload.get("out_of_scope") or [],
    )
    generated_files = generation.get("files") or []
    files_to_create = [file_entry.get("path") for file_entry in generated_files]

    return {
        "success": bool(generation.get("success")),
        "agent_id": "builder_agent",
        "message": (
            "Builder Agent produced request-specific DB-preview artifacts."
            if generation.get("success")
            else f"Builder Agent could not generate a valid application: {generation.get('blocked_reason')}"
        ),
        "goal": goal,
        "source_task_id": source_task_id,
        "dependency_context": dependency_context,
        "implementation_plan": {
            "app_name": generation.get("app_name"),
            "summary": generation.get("summary"),
            "files_to_create": files_to_create,
            "generated_file_count": len(generated_files),
            "dependency_context_available": dependency_context.get("context_available"),
            "assumptions": generation.get("assumptions") or [],
            "risks": generation.get("risks") or [],
            "safe_mode": True,
            "writes_code": bool(generation.get("success")),
            "write_mode": "db_preview_only",
            "reason": (
                "Files are generated by a real model call grounded in the approved scope of work, "
                "then persisted as DB-preview artifacts. No disk write, filesystem write, deployment, "
                "materialization, dependency install, or generated-code execution is performed here; "
                "those remain separate, explicitly gated steps."
            ),
            "generation": generation.get("generation") or {},
            "blocked_reason": generation.get("blocked_reason"),
            "failed_checks": generation.get("failed_checks") or [],
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


_REVIEW_CHECKLIST = [
    "Validate architecture matches user goal",
    "Check security-sensitive operations",
    "Check database model consistency",
    "Check API route naming",
    "Check approval requirement for risky actions",
    "Check tests are defined before deployment",
    "Confirm generated artifacts remain DB-preview only before materialization approval",
]


def _reviewer_checklist_only(goal: str, message: str) -> Dict[str, Any]:
    return {
        "success": True,
        "agent_id": "reviewer_agent",
        "message": message,
        "goal": goal,
        "review_checklist": _REVIEW_CHECKLIST,
        "independent_review_performed": False,
        "next_recommended_task": "test_task",
    }


def reviewer_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    """Independently reviews the builder's generated files with a swapped-provider
    model, and - if it finds blocking issues - runs one bounded repair attempt
    with the builder's own provider before letting the build proceed.

    Falls back to the old decorative checklist-only behavior whenever there is
    nothing to review (no builder output) or the independent reviewer itself is
    unavailable, so a provider outage never blocks a build that would otherwise
    succeed.
    """
    goal = _goal(task)
    input_payload = task.get("input_payload") or {}
    builder_output = _dependency_output_for_step(task, "builder")
    generated_files = builder_output.get("generated_files") or []
    builder_generation = (builder_output.get("implementation_plan") or {}).get("generation") or {}
    builder_provider = builder_generation.get("provider")

    if not generated_files or not builder_provider:
        return _reviewer_checklist_only(
            goal,
            "Reviewer Agent produced a review checklist (no generated files were available to independently review).",
        )

    review_provider = _other_provider(builder_provider)
    review = review_app_build_files(
        app_request=str(input_payload.get("app_request") or goal),
        scope_of_work_markdown=str(input_payload.get("scope_of_work_markdown") or ""),
        acceptance_criteria=input_payload.get("acceptance_criteria") or [],
        out_of_scope=input_payload.get("out_of_scope") or [],
        generated_files=generated_files,
        provider=review_provider,
    )

    if review is None:
        return _reviewer_checklist_only(
            goal,
            f"Reviewer Agent produced a review checklist (independent review via {review_provider} was unavailable).",
        )

    if review.get("approved"):
        return {
            "success": True,
            "agent_id": "reviewer_agent",
            "message": f"Reviewer Agent (independent review via {review.get('provider')}) approved the generated application with no blocking findings.",
            "goal": goal,
            "review_checklist": _REVIEW_CHECKLIST,
            "independent_review_performed": True,
            "independent_review": review,
            "next_recommended_task": "test_task",
        }

    repair = repair_app_build_files(
        app_request=str(input_payload.get("app_request") or goal),
        scope_of_work_markdown=str(input_payload.get("scope_of_work_markdown") or ""),
        acceptance_criteria=input_payload.get("acceptance_criteria") or [],
        out_of_scope=input_payload.get("out_of_scope") or [],
        previous_files=generated_files,
        review_findings=review.get("findings") or [],
        provider=builder_provider,
    )

    if not repair.get("success"):
        return {
            "success": False,
            "agent_id": "reviewer_agent",
            "message": (
                f"Reviewer Agent (independent review via {review.get('provider')}) found blocking issues "
                f"and the automatic repair attempt did not resolve them: {repair.get('blocked_reason')}"
            ),
            "goal": goal,
            "review_checklist": _REVIEW_CHECKLIST,
            "independent_review_performed": True,
            "independent_review": review,
            "repair_attempted": True,
            "repair_blocked_reason": repair.get("blocked_reason"),
            "next_recommended_task": None,
        }

    repaired_files = repair.get("files") or []
    return {
        "success": True,
        "agent_id": "reviewer_agent",
        "message": (
            f"Reviewer Agent (independent review via {review.get('provider')}) found "
            f"{len(review.get('findings') or [])} issue(s) and repaired them via {builder_provider}."
        ),
        "goal": goal,
        "review_checklist": _REVIEW_CHECKLIST,
        "independent_review_performed": True,
        "independent_review": review,
        "repair_attempted": True,
        "repair_result": {
            "app_name": repair.get("app_name"),
            "summary": repair.get("summary"),
            "generated_file_count": len(repaired_files),
            "generation": repair.get("generation") or {},
        },
        "generated_files": repaired_files,
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "filesystem_write_performed": False,
        "generated_code_execution_performed": False,
        "external_deployment_performed": False,
        "materialization_performed": False,
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
