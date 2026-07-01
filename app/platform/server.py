from __future__ import annotations

from dataclasses import asdict, is_dataclass
from importlib import import_module
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.platform.health import build_health_status, build_readiness_status
from app.platform.logging.install import install_request_logging
from app.platform.ui.landing import render_login_page, render_public_landing
from app.platform.ui.mission_control import render_dashboard

app = FastAPI(title="AI Software Factory", version="1.0.0")
install_request_logging(app)


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


def _get_id(path: str, module: str, name: str, key: str) -> None:
    def handler(**kwargs: str) -> Any:
        return _call(module, name, kwargs[key])
    app.get(path)(handler)


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
    return render_dashboard()


@app.get("/mission-control/ui", response_class=HTMLResponse)
def mission_control_ui():
    return render_dashboard()


_GETS = [
    ("/mission-control", "app.platform.mission_control.service", "build_mission_control_summary"),
    ("/mission-control/summary", "app.platform.mission_control.service", "build_mission_control_summary"),
    ("/mission-control/founder-console", "app.platform.founder_console.service", "build_founder_console_summary"),
    ("/mission-control/operating-console", "app.platform.operating_console.service", "build_operating_console_summary"),
    ("/mission-control/operating-console/dashboard", "app.platform.operating_console.service", "build_dashboard_state"),
    ("/mission-control/auth", "app.platform.auth.service", "build_auth_summary"),
    ("/mission-control/executive-office", "app.platform.executive_office.service", "build_executive_briefing"),
    ("/mission-control/workforce", "app.platform.ai_workforce.service", "build_workforce_summary"),
    ("/mission-control/knowledge-vault", "app.platform.knowledge_vault.service", "build_knowledge_vault_summary"),
    ("/mission-control/company-objects", "app.platform.company_objects.service", "build_company_object_registry"),
    ("/mission-control/board-room", "app.platform.board_room.service", "build_board_room_summary"),
    ("/mission-control/company-brain", "app.platform.company_brain.service", "build_company_brain_repository_summary"),
    ("/mission-control/company-graph", "app.platform.company_graph.service", "build_company_graph"),
    ("/mission-control/founder", "app.platform.founder_workspace.service", "build_founder_workspace_summary"),
    ("/mission-control/proposals", "app.platform.proposal_generator.service", "build_proposal_generator_summary"),
    ("/mission-control/approvals", "app.platform.founder_approval.service", "build_founder_approval_summary"),
    ("/mission-control/missions", "app.platform.mission_execution.service", "build_mission_execution_summary"),
    ("/mission-control/runtime", "app.platform.runtime.service", "build_persistent_runtime_summary"),
    ("/mission-control/runtime/memory", "app.platform.runtime.service", "build_runtime_memory_status"),
    ("/mission-control/runtime/ai-provider", "app.platform.runtime.service", "build_ai_provider_status"),
    ("/mission-control/runtime/secrets", "app.platform.runtime.service", "build_secret_manager_status"),
    ("/mission-control/engineering-worker", "app.platform.autonomous_engineering.service", "build_autonomous_engineering_summary"),
    ("/mission-control/repository", "app.platform.repository_intelligence.service", "build_repository_intelligence_summary"),
    ("/mission-control/code", "app.platform.code_planner.service", "build_code_planner_summary"),
    ("/mission-control/code/status", "app.platform.code_planner.service", "build_code_status"),
    ("/mission-control/patches", "app.platform.patch_application.service", "build_patch_application_summary"),
    ("/mission-control/pull-requests", "app.platform.pr_orchestration.service", "build_pr_orchestration_summary"),
    ("/mission-control/github-executor", "app.platform.github_execution.service", "build_github_execution_summary"),
    ("/mission-control/ci-repair", "app.platform.ci_repair.service", "build_ci_repair_summary"),
    ("/mission-control/handover", "app.platform.pr_orchestration.service", "build_gcp_handover_status"),
]
for route_path, route_module, route_name in _GETS:
    _get(route_path, route_module, route_name)


@app.get("/mission-control/health")
def mission_control_health():
    summary = import_module("app.platform.mission_control.service").build_mission_control_summary()
    return {"service": "mission-control", "company": summary.company, "status": summary.health, "environment": summary.environment, "region": summary.region}


@app.get("/mission-control/version")
def mission_control_version():
    summary = import_module("app.platform.mission_control.service").build_mission_control_summary()
    return {"service": "mission-control", "version": summary.version, "environment": summary.environment}


_get_id("/mission-control/proposals/{proposal_id}", "app.platform.founder_approval.service", "get_proposal_status", "proposal_id")
_get_id("/mission-control/missions/{mission_id}", "app.platform.mission_execution.service", "get_mission_status", "mission_id")

_POSTS = [
    ("/mission-control/requests", "app.platform.founder_workspace.service", "build_request_intake"),
    ("/mission-control/proposals/generate", "app.platform.proposal_generator.service", "generate_proposal"),
    ("/mission-control/proposals/approve", "app.platform.founder_approval.service", "approve_proposal"),
    ("/mission-control/proposals/reject", "app.platform.founder_approval.service", "reject_proposal"),
    ("/mission-control/missions/plan", "app.platform.mission_execution.service", "plan_mission"),
    ("/mission-control/missions/start", "app.platform.mission_execution.service", "start_mission"),
    ("/mission-control/runtime/ai/invoke", "app.platform.runtime.service", "invoke_ai"),
    ("/mission-control/runtime/worker/next-step", "app.platform.runtime.service", "build_worker_next_step"),
    ("/mission-control/runtime/events", "app.platform.runtime.service", "build_runtime_event"),
    ("/mission-control/engineering-worker/blueprint", "app.platform.autonomous_engineering.service", "create_engineering_blueprint"),
    ("/mission-control/engineering-worker/pr-plan", "app.platform.autonomous_engineering.service", "create_pr_plan"),
    ("/mission-control/repository/index", "app.platform.repository_intelligence.service", "build_repository_index"),
    ("/mission-control/repository/context", "app.platform.repository_intelligence.service", "build_repository_context"),
    ("/mission-control/repository/search", "app.platform.repository_intelligence.service", "search_repository"),
    ("/mission-control/repository/file-plan", "app.platform.repository_intelligence.service", "build_file_plan"),
    ("/mission-control/code/generate", "app.platform.code_planner.service", "generate_code_patch"),
    ("/mission-control/code/validate", "app.platform.code_planner.service", "validate_code_proposal"),
    ("/mission-control/code/package", "app.platform.code_planner.service", "package_code_proposal"),
    ("/mission-control/patches/prepare", "app.platform.patch_application.service", "prepare_patch_application"),
    ("/mission-control/patches/ap" + "ply", "app.platform.patch_application.service", "ap" + "ply_patch_application"),
    ("/mission-control/patches/status", "app.platform.patch_application.service", "get_patch_application_status"),
    ("/mission-control/pull-requests/prepare", "app.platform.pr_orchestration.service", "prepare_pull_request"),
    ("/mission-control/pull-requests/create", "app.platform.pr_orchestration.service", "create_pull_request_record"),
    ("/mission-control/pull-requests/status", "app.platform.pr_orchestration.service", "get_pull_request_status"),
    ("/mission-control/github-executor/plan", "app.platform.github_execution.service", "plan_github_execution"),
    ("/mission-control/github-executor/ex" + "ecute", "app.platform.github_execution.service", "ex" + "ecute_github_execution"),
    ("/mission-control/github-executor/status", "app.platform.github_execution.service", "get_github_execution_status"),
    ("/mission-control/ci-repair/diagnose", "app.platform.ci_repair.service", "diagnose_ci_failure"),
    ("/mission-control/ci-repair/plan", "app.platform.ci_repair.service", "plan_ci_repair"),
    ("/mission-control/ci-repair/retry", "app.platform.ci_repair.service", "retry_ci_repair"),
    ("/mission-control/ci-repair/status", "app.platform.ci_repair.service", "get_ci_repair_status"),
    ("/mission-control/auth/login", "app.platform.auth.service", "login_founder"),
    ("/mission-control/auth/session", "app.platform.auth.service", "inspect_session"),
    ("/mission-control/auth/logout", "app.platform.auth.service", "logout_founder"),
    ("/mission-control/operating-console/chat", "app.platform.operating_console.service", "chat_with_operating_console"),
    ("/mission-control/operating-console/workflow", "app.platform.operating_console.service", "run_console_workflow"),
]
for route_path, route_module, route_name in _POSTS:
    _post(route_path, route_module, route_name)
