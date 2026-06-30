from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.platform.ai_workforce.service import build_workforce_summary
from app.platform.executive_office.service import build_executive_briefing
from app.platform.health import build_health_status, build_readiness_status
from app.platform.knowledge_vault.service import build_knowledge_vault_summary
from app.platform.logging.install import install_request_logging
from app.platform.mission_control.service import build_mission_control_summary
from app.platform.ui.mission_control import render_dashboard
from app.platform.company_objects.service import build_company_object_registry
from app.platform.board_room.service import build_board_room_summary
from app.platform.company_brain.service import build_company_brain_repository_summary
from app.platform.company_graph.service import build_company_graph
from app.platform.founder_workspace.service import build_founder_workspace_summary, build_request_intake
from app.platform.proposal_generator.service import build_proposal_generator_summary, generate_proposal
from app.platform.founder_approval.service import (
    approve_proposal,
    build_founder_approval_summary,
    get_proposal_status,
    reject_proposal,
)
from app.platform.mission_execution.service import (
    build_mission_execution_summary,
    get_mission_status,
    plan_mission,
    start_mission,
)
from app.platform.runtime.service import (
    build_ai_provider_status,
    build_persistent_runtime_summary,
    build_runtime_event,
    build_runtime_memory_status,
    build_secret_manager_status,
)

app = FastAPI(title="AI Software Factory", version="1.0.0")
install_request_logging(app)


@app.get("/")
def root():
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


@app.get("/mission-control")
def mission_control():
    return asdict(build_mission_control_summary())


@app.get("/mission-control/summary")
def mission_control_summary():
    return asdict(build_mission_control_summary())


@app.get("/mission-control/health")
def mission_control_health():
    summary = build_mission_control_summary()
    return {
        "service": "mission-control",
        "company": summary.company,
        "status": summary.health,
        "environment": summary.environment,
        "region": summary.region,
    }


@app.get("/mission-control/version")
def mission_control_version():
    summary = build_mission_control_summary()
    return {
        "service": "mission-control",
        "version": summary.version,
        "environment": summary.environment,
    }


@app.get("/mission-control/executive-office")
def executive_office():
    return build_executive_briefing()

@app.get("/mission-control/workforce")
def workforce():
    return build_workforce_summary()

@app.get("/mission-control/knowledge-vault")
def knowledge_vault():
    return build_knowledge_vault_summary()


@app.get("/mission-control/company-objects")
def company_objects():
    return build_company_object_registry()


@app.get("/mission-control/board-room")
def board_room():
    return build_board_room_summary()


@app.get("/mission-control/company-brain")
def company_brain():
    return build_company_brain_repository_summary()


@app.get("/mission-control/company-graph")
def company_graph():
    return build_company_graph()


@app.get("/mission-control/founder")
def founder_workspace():
    return build_founder_workspace_summary()


@app.post("/mission-control/requests")
def request_intake(payload: dict):
    return build_request_intake(payload)


@app.get("/mission-control/proposals")
def proposal_generator():
    return build_proposal_generator_summary()


@app.post("/mission-control/proposals/generate")
def proposal_generate(payload: dict):
    return generate_proposal(payload)


@app.get("/mission-control/approvals")
def founder_approval():
    return build_founder_approval_summary()


@app.get("/mission-control/proposals/{proposal_id}")
def proposal_status(proposal_id: str):
    return get_proposal_status(proposal_id)


@app.post("/mission-control/proposals/approve")
def proposal_approve(payload: dict):
    return approve_proposal(payload)


@app.post("/mission-control/proposals/reject")
def proposal_reject(payload: dict):
    return reject_proposal(payload)


@app.get("/mission-control/missions")
def missions():
    return build_mission_execution_summary()


@app.get("/mission-control/missions/{mission_id}")
def mission_status(mission_id: str):
    return get_mission_status(mission_id)


@app.post("/mission-control/missions/plan")
def mission_plan(payload: dict):
    return plan_mission(payload)


@app.post("/mission-control/missions/start")
def mission_start(payload: dict):
    return start_mission(payload)


@app.get("/mission-control/runtime")
def persistent_runtime():
    return build_persistent_runtime_summary()


@app.get("/mission-control/runtime/memory")
def runtime_memory():
    return build_runtime_memory_status()


@app.get("/mission-control/runtime/ai-provider")
def runtime_ai_provider():
    return build_ai_provider_status()


@app.get("/mission-control/runtime/secrets")
def runtime_secrets():
    return build_secret_manager_status()


@app.post("/mission-control/runtime/events")
def runtime_events(payload: dict):
    return build_runtime_event(payload)
