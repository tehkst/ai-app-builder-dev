from __future__ import annotations

from dataclasses import asdict, is_dataclass
from importlib import import_module
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.platform.health import build_health_status, build_readiness_status
from app.platform.logging.install import install_request_logging
from app.platform.ui.auth_safe_dashboard import render_auth_safe_dashboard
from app.platform.ui.landing import render_login_page, render_public_landing

app = FastAPI(title="AI Software Factory", version="1.0.0")
install_request_logging(app)


@app.on_event("startup")
def migrate_platform_execution_layer() -> None:
    from app.platform.persistence.execution_migrations import run_execution_layer_migrations
    run_execution_layer_migrations()


def _json(value: Any) -> Any:
    return asdict(value) if is_dataclass(value) else value


def _call(module: str, name: str, *args: Any) -> Any:
    return _json(getattr(import_module(module), name)(*args))


def _get(path: str, module: str, name: str) -> None:
    def handler() -> Any:
        return _call(module, name)
    app.get(path)(handler)


def _post(path: str, module: str, name: str) -> None:
    def handler(payload: dict) -> Any:
        return _call(module, name, payload)
    app.post(path)(handler)


@app.get("/", response_class=HTMLResponse)
def root():
    return render_public_landing()


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return render_login_page()


@app.get("/status")
def status():
    return {"service": "ai-software-factory", "status": "running"}


@app.get("/health")
def health():
    return build_health_status()


@app.get("/ready")
def ready():
    return build_readiness_status()


@app.get("/ui", response_class=HTMLResponse)
def ui():
    return render_public_landing()


@app.get("/mission-control/ui", response_class=HTMLResponse)
def mission_control_ui():
    return render_auth_safe_dashboard()


@app.get("/mission-control/proposals/{proposal_id}")
def proposal_status(proposal_id: str):
    return _call("app.platform.founder_approval.service", "get_proposal_status", proposal_id)


@app.get("/mission-control/missions/{mission_id}")
def mission_status(mission_id: str):
    return _call("app.platform.mission_execution.service", "get_mission_status", mission_id)


@app.get("/mission-control/pipeline/{mission_id}")
def pipeline_mission_status(mission_id: str):
    return _call("app.platform.pipeline.mission_pipeline", "get_pipeline_mission", mission_id)


@app.get("/mission-control/pipeline/{mission_id}/timeline")
def pipeline_mission_timeline(mission_id: str):
    return _call("app.platform.pipeline.mission_pipeline", "get_pipeline_mission_timeline", mission_id)


@app.get("/mission-control/pipeline/{mission_id}/recommendation")
def pipeline_mission_recommendation(mission_id: str):
    return _call("app.platform.pipeline.mission_pipeline", "get_pipeline_mission_recommendation", mission_id)


_get("/mission-control", "app.platform.mission_control.service", "build_mission_control_summary")
_get("/mission-control/summary", "app.platform.mission_control.service", "build_mission_control_summary")
_get("/mission-control/founder-console", "app.platform.founder_console.service", "build_founder_console_summary")
_get("/mission-control/operating-console", "app.platform.constitution.board_room_binding", "build_operating_console_summary")
_get("/mission-control/operating-console/dashboard", "app.platform.constitution.board_room_binding", "build_dashboard_state")
_get("/mission-control/company-intelligence", "app.platform.company_intelligence.service", "build_company_intelligence_summary")
_get("/mission-control/company-intelligence/snapshot", "app.platform.company_intelligence.service", "build_company_intelligence_snapshot")
_get("/mission-control/constitution", "app.platform.constitution.service", "build_constitution_summary")
_get("/mission-control/governance-authorization", "app.platform.governance_authorization.service", "build_governance_authorization_summary")
_get("/mission-control/validation", "app.platform.validation.service", "build_validation_summary")
_get("/mission-control/validation/acceptance", "app.platform.validation.service", "build_acceptance_report")
_get("/mission-control/conversation-intelligence", "app.platform.conversation_intelligence.service", "build_conversation_intelligence_summary")
_get("/mission-control/executive-decision", "app.platform.executive_decision.service", "build_executive_decision_summary")
_get("/mission-control/executive-intelligence", "app.platform.executive_intelligence.service", "build_executive_intelligence_summary")
_get("/mission-control/executive-intelligence/briefing", "app.platform.executive_intelligence.service", "build_executive_intelligence_briefing")
_get("/mission-control/auth", "app.platform.auth.service", "build_auth_summary")
_get("/mission-control/health", "app.platform.mission_control.service", "build_mission_control_summary")
_get("/mission-control/version", "app.platform.mission_control.service", "build_mission_control_summary")
_get("/mission-control/executive-office", "app.platform.executive_office.service", "build_executive_briefing")
_get("/mission-control/workforce", "app.platform.ai_workforce.service", "build_workforce_summary")
_get("/mission-control/knowledge-vault", "app.platform.knowledge_vault.service", "build_knowledge_vault_summary")
_get("/mission-control/company-objects", "app.platform.company_objects.service", "build_company_object_registry")
_get("/mission-control/board-room", "app.platform.board_room.service", "build_board_room_summary")
_get("/mission-control/company-brain", "app.platform.company_brain.service", "build_company_brain_repository_summary")
_get("/mission-control/company-graph", "app.platform.company_graph.service", "build_company_graph")
_get("/mission-control/founder", "app.platform.founder_workspace.service", "build_founder_workspace_summary")
_get("/mission-control/proposals", "app.platform.proposal_generator.service", "build_proposal_generator_summary")
_get("/mission-control/approvals", "app.platform.founder_approval.service", "build_founder_approval_summary")
_get("/mission-control/missions", "app.platform.mission_execution.service", "build_mission_execution_summary")
_get("/mission-control/founder-workflows", "app.platform.founder_workflow.service", "build_founder_workflow_summary")
_get("/mission-control/planning", "app.platform.planning.service", "build_planning_summary")
_get("/mission-control/engineering-manager", "app.platform.engineering_manager.service", "build_engineering_manager_summary")
_get("/mission-control/pipeline", "app.platform.pipeline.mission_pipeline", "build_mission_pipeline_summary")
_get("/mission-control/execution", "app.platform.operating_console.mission_run_service", "build_mission_execution_summary")
_get("/mission-control/github", "app.platform.github.service", "build_github_summary")
_get("/mission-control/runtime", "app.platform.runtime.service", "build_persistent_runtime_summary")
_get("/mission-control/persistence", "app.platform.persistence.readiness", "build_platform_persistence_readiness")
_get("/mission-control/runtime/memory", "app.platform.runtime.service", "build_runtime_memory_status")
_get("/mission-control/runtime/ai-provider", "app.platform.runtime.service", "build_ai_provider_status")
_get("/mission-control/runtime/secrets", "app.platform.runtime.service", "build_secret_manager_status")
_get("/mission-control/engineering-worker", "app.platform.autonomous_engineering.service", "build_autonomous_engineering_summary")
_get("/mission-control/repository", "app.platform.repository_intelligence.service", "build_repository_intelligence_summary")
_get("/mission-control/code", "app.platform.code_planner.service", "build_code_planner_summary")
_get("/mission-control/code/status", "app.platform.code_planner.service", "build_code_status")
_get("/mission-control/patches", "app.platform.patch_application.service", "build_patch_application_summary")
_get("/mission-control/pull-requests", "app.platform.pr_orchestration.service", "build_pr_orchestration_summary")
_get("/mission-control/github-executor", "app.platform.github_execution.service", "build_github_execution_summary")
_get("/mission-control/github-execution", "app.platform.github_execution.approved_executor", "build_approved_github_execution_summary")
_get("/mission-control/github-pr", "app.platform.github_execution.pr_lifecycle", "build_github_pr_summary")
_get("/mission-control/github-merge", "app.platform.github_execution.approved_merge", "build_github_merge_summary")
_get("/mission-control/deployment", "app.platform.deployment.approved_cloud_run", "build_cloud_run_deployment_summary")
_get("/mission-control/verification", "app.platform.deployment.production_verification", "build_production_verification_summary")
_get("/mission-control/rollback", "app.platform.deployment.approved_rollback", "build_cloud_run_rollback_summary")
_get("/mission-control/ci-repair", "app.platform.ci_repair.service", "build_ci_repair_summary")
_get("/mission-control/handover", "app.platform.pr_orchestration.service", "build_gcp_handover_status")

_post("/mission-control/operating-console/chat", "app.platform.constitution.board_room_binding", "chat_with_operating_console")
_post("/mission-control/operating-console/workflow", "app.platform.constitution.board_room_binding", "run_console_workflow")
_post("/mission-control/operating-console/action", "app.platform.operating_console.action_service", "dispatch_board_room_action")
_post("/mission-control/operating-console/action/status", "app.platform.operating_console.mission_run_service", "get_mission_run_status")
_post("/mission-control/conversation-intelligence/analyze", "app.platform.conversation_intelligence.service", "analyze_conversation")
_post("/mission-control/executive-decision/decide", "app.platform.executive_decision.service", "decide_next_action")
_post("/mission-control/governance-authorization/authorize", "app.platform.governance_authorization.service", "authorize_governed_action")
_post("/mission-control/governance-authorization/evidence", "app.platform.governance_authorization.service", "get_governance_evidence")
_post("/mission-control/governance-authorization/approvals", "app.platform.governance_authorization.approvals", "create_durable_approval")
_post("/mission-control/governance-authorization/approvals/revoke", "app.platform.governance_authorization.approvals", "revoke_durable_approval")
_post("/mission-control/validation/run", "app.platform.validation.service", "run_validation_mission")
_post("/mission-control/validation/status", "app.platform.validation.service", "get_validation_mission")
_post("/mission-control/execution-workspaces/action", "app.platform.workspaces.governed_service", "execute_workspace_action")
_post("/mission-control/repository-execution/action", "app.platform.execution.repository_adapter", "execute_repository_action")
_post("/mission-control/github-operations/action", "app.platform.github_execution.adapter", "execute_github_action")
_post("/mission-control/releases/action", "app.platform.release.execution_adapter", "execute_release_action")
_post("/mission-control/auth/login", "app.platform.auth.service", "login_founder")
_post("/mission-control/auth/session", "app.platform.auth.service", "inspect_session")
_post("/mission-control/auth/logout", "app.platform.auth.service", "logout_founder")
_post("/mission-control/requests", "app.platform.founder_workspace.service", "build_request_intake")
_post("/mission-control/proposals/generate", "app.platform.proposal_generator.service", "generate_proposal")
_post("/mission-control/proposals/approve", "app.platform.founder_approval.service", "approve_proposal")
_post("/mission-control/proposals/reject", "app.platform.founder_approval.service", "reject_proposal")
_post("/mission-control/missions/plan", "app.platform.mission_execution.service", "plan_mission")
_post("/mission-control/missions/start", "app.platform.mission_execution.service", "start_mission")
_post("/mission-control/founder-workflows/create", "app.platform.founder_workflow.service", "create_founder_workflow")
_post("/mission-control/founder-workflows/advance", "app.platform.founder_workflow.service", "advance_founder_workflow")
_post("/mission-control/founder-workflows/status", "app.platform.founder_workflow.service", "get_founder_workflow_status")
_post("/mission-control/execution/create", "app.platform.execution.service", "create_execution_mission")
_post("/mission-control/planning/generate", "app.platform.planning.service", "generate_engineering_plan")
_post("/mission-control/engineering-manager/breakdown", "app.platform.engineering_manager.service", "create_engineering_breakdown")
_post("/mission-control/execution/from-board-room", "app.platform.execution.orchestrator", "create_mission_from_board_room")
_post("/mission-control/execution/advance", "app.platform.operating_console.mission_run_service", "continue_mission_run")
_post("/mission-control/github/health", "app.platform.github.service", "github_health")
_post("/mission-control/runtime/ai/invoke", "app.platform.runtime.service", "invoke_ai")
_post("/mission-control/runtime/worker/next-step", "app.platform.runtime.service", "build_worker_next_step")
_post("/mission-control/runtime/events", "app.platform.runtime.service", "build_runtime_event")
_post("/mission-control/engineering-worker/blueprint", "app.platform.autonomous_engineering.service", "create_engineering_blueprint")
_post("/mission-control/engineering-worker/pr-plan", "app.platform.autonomous_engineering.service", "create_pr_plan")
_post("/mission-control/repository/index", "app.platform.repository_intelligence.service", "build_repository_index")
_post("/mission-control/repository/context", "app.platform.repository_intelligence.service", "build_repository_context")
_post("/mission-control/repository/search", "app.platform.repository_intelligence.service", "search_repository")
_post("/mission-control/repository/file-plan", "app.platform.repository_intelligence.service", "build_file_plan")
_post("/mission-control/code/generate", "app.platform.code_planner.service", "generate_code_patch")
_post("/mission-control/code/validate", "app.platform.code_planner.service", "validate_code_proposal")
_post("/mission-control/code/package", "app.platform.code_planner.service", "package_code_proposal")
_post("/mission-control/patches/prepare", "app.platform.patch_application.service", "prepare_patch_application")
_post("/mission-control/patches/apply", "app.platform.patch_application.service", "apply_patch_application")
_post("/mission-control/patches/status", "app.platform.patch_application.service", "get_patch_application_status")
_post("/mission-control/pull-requests/prepare", "app.platform.pr_orchestration.service", "prepare_pull_request")
_post("/mission-control/pull-requests/create", "app.platform.pr_orchestration.service", "create_pull_request_record")
_post("/mission-control/pull-requests/status", "app.platform.pr_orchestration.service", "get_pull_request_status")
_post("/mission-control/github-executor/plan", "app.platform.github_execution.service", "plan_github_execution")
_post("/mission-control/github-executor/execute", "app.platform.github_execution.service", "execute_github_execution")
_post("/mission-control/github-executor/status", "app.platform.github_execution.service", "get_github_execution_status")
_post("/mission-control/github-execution/preview", "app.platform.github_execution.approved_executor", "preview_approved_github_execution")
_post("/mission-control/github-execution/execute", "app.platform.github_execution.approved_executor", "execute_approved_github_execution")
_post("/mission-control/github-pr/status", "app.platform.github_execution.pr_lifecycle", "get_github_pr_status")
_post("/mission-control/github-merge/preview", "app.platform.github_execution.approved_merge", "preview_github_merge")
_post("/mission-control/github-merge/execute", "app.platform.github_execution.approved_merge", "execute_github_merge")
_post("/mission-control/deployment/preview", "app.platform.deployment.approved_cloud_run", "preview_cloud_run_deployment")
_post("/mission-control/deployment/execute", "app.platform.deployment.approved_cloud_run", "execute_cloud_run_deployment")
_post("/mission-control/verification/run", "app.platform.deployment.production_verification", "run_production_verification")
_post("/mission-control/rollback/preview", "app.platform.deployment.approved_rollback", "preview_cloud_run_rollback")
_post("/mission-control/rollback/execute", "app.platform.deployment.approved_rollback", "execute_cloud_run_rollback")
_post("/mission-control/ci-repair/diagnose", "app.platform.ci_repair.service", "diagnose_ci_failure")
_post("/mission-control/ci-repair/plan", "app.platform.ci_repair.service", "plan_ci_repair")
_post("/mission-control/ci-repair/retry", "app.platform.ci_repair.service", "retry_ci_repair")
_post("/mission-control/ci-repair/status", "app.platform.ci_repair.service", "get_ci_repair_status")

# ---------------------------------------------------------------------------
# Native Coding Agent routes (feature-flag-gated)
# ---------------------------------------------------------------------------
_post("/mission-control/coding-agent/start", "app.platform.coding_agent.integration", "route_mission_to_coding_agent")
_post("/mission-control/coding-agent/task-status", "app.platform.coding_agent.integration", "get_coding_agent_task_status")
_post("/mission-control/coding-agent/em-dispatch", "app.platform.coding_agent.integration", "engineering_manager_dispatch_to_coding_agent")
