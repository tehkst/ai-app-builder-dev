from __future__ import annotations

from typing import Any, Dict

from app.platform.agents.registry import AgentDefinition, register_agent
from app.platform.agents.factory import agent_factory_handler
from app.platform.services.app_generation_service import (
    generate_app_build_files,
    repair_app_build_files,
    review_app_build_files,
)
from app.platform.architecture_agent.service import create_architecture_decision
from app.platform.agents.workflow_step_context import (
    _goal,
    _source_task_id,
    _dependency_context,
    _dependency_output_for_step,
)


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
