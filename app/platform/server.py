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


_get("/mission-control", "app.platform.mission_control.service", "build_mission_control_summary")
_get("/mission-control/summary", "app.platform.mission_control.service", "build_mission_control_summary")
_get("/mission-control/founder-console", "app.platform.founder_console.service", "build_founder_console_summary")
_get("/mission-control/operating-console", "app.platform.operating_console.service", "build_operating_console_summary")
_get("/mission-control/operating-console/dashboard", "app.platform.operating_console.service", "build_dashboard_state")
_get("/mission-control/auth", "app.platform.auth.service", "build_auth_summary")
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
_get("/mission-control/runtime", "app.platform.runtime.service", "build_persistent_runtime_summary")
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
_get("/mission-control/ci-repair", "app.platform.ci_repair.service", "build_ci_repair_summary")
_get("/mission-control/handover", "app.platform.pr_orchestration.service", "build_gcp_handover_status")
